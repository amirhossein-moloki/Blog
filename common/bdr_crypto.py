import os
import io
import struct
import zlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

def derive_key(passphrase: str, salt: bytes, iterations: int = 100000) -> bytes:
    """
    Derive a 256-bit AES key from the passphrase and salt using PBKDF2HMAC.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(passphrase.encode("utf-8"))

class GzipEncryptionStream:
    """
    A file-like object that intercepts compressed bytes written to it,
    buffers them, and writes them out as AES-256-GCM encrypted chunks.
    """
    def __init__(self, out_file, passphrase):
        self.out_file = out_file
        self.passphrase = passphrase
        self.buffer = io.BytesIO()
        self.chunk_size = 65536
        self.chunk_index = 0

        self.salt = os.urandom(16)
        self.iterations = 100000
        key = derive_key(self.passphrase, self.salt, self.iterations)
        self.aesgcm = AESGCM(key)

        # Write format magic bytes and metadata header
        self.out_file.write(b"BDRGCMv1")
        self.out_file.write(self.salt)
        self.out_file.write(struct.pack(">I", self.iterations))

    def write(self, data):
        self.buffer.write(data)
        self.buffer.seek(0, io.SEEK_END)
        if self.buffer.tell() >= self.chunk_size:
            self.buffer.seek(0)
            while True:
                chunk = self.buffer.read(self.chunk_size)
                if len(chunk) < self.chunk_size:
                    remaining = chunk
                    self.buffer = io.BytesIO()
                    self.buffer.write(remaining)
                    break
                self._encrypt_and_write_chunk(chunk)
        return len(data)

    def _encrypt_and_write_chunk(self, chunk):
        nonce = os.urandom(12)
        aad = struct.pack(">Q", self.chunk_index)
        ciphertext = self.aesgcm.encrypt(nonce, chunk, aad)
        combined_len = len(ciphertext)
        self.out_file.write(struct.pack(">I", combined_len))
        self.out_file.write(nonce)
        self.out_file.write(ciphertext)
        self.chunk_index += 1

    def flush(self):
        pass

    def close(self):
        self.buffer.seek(0)
        remaining = self.buffer.read()
        if remaining:
            self._encrypt_and_write_chunk(remaining)
        # Write EOF marker
        self.out_file.write(struct.pack(">I", 0))


def encrypt_stream(instream, outstream, passphrase: str, chunk_size: int = 65536):
    """
    Encrypts data from instream and writes it to outstream in an authenticated, streaming manner.
    """
    salt = os.urandom(16)
    iterations = 100000
    key = derive_key(passphrase, salt, iterations)
    aesgcm = AESGCM(key)

    # Write header
    outstream.write(b"BDRGCMv1")
    outstream.write(salt)
    outstream.write(struct.pack(">I", iterations))

    chunk_index = 0
    while True:
        chunk = instream.read(chunk_size)
        if not chunk:
            break

        nonce = os.urandom(12)
        aad = struct.pack(">Q", chunk_index)

        ciphertext = aesgcm.encrypt(nonce, chunk, aad)
        combined_len = len(ciphertext)

        outstream.write(struct.pack(">I", combined_len))
        outstream.write(nonce)
        outstream.write(ciphertext)
        chunk_index += 1

    # Write clean EOF marker
    outstream.write(struct.pack(">I", 0))


def decrypt_stream(instream, outstream, passphrase: str):
    """
    Decrypts AES-256-GCM encrypted data from instream and writes verified plaintext to outstream.
    """
    magic = instream.read(8)
    if magic != b"BDRGCMv1":
        raise ValueError("Invalid backup file format or magic bytes mismatch.")

    salt = instream.read(16)
    if len(salt) < 16:
        raise ValueError("Corrupted backup: missing salt.")

    iter_bytes = instream.read(4)
    if len(iter_bytes) < 4:
        raise ValueError("Corrupted backup: missing iterations.")
    iterations = struct.unpack(">I", iter_bytes)[0]

    key = derive_key(passphrase, salt, iterations)
    aesgcm = AESGCM(key)

    chunk_index = 0
    while True:
        len_bytes = instream.read(4)
        if len(len_bytes) < 4:
            raise ValueError("Corrupted backup: unexpected EOF while reading chunk length.")
        chunk_len = struct.unpack(">I", len_bytes)[0]

        if chunk_len == 0:
            break

        nonce = instream.read(12)
        if len(nonce) < 12:
            raise ValueError("Corrupted backup: missing nonce.")

        ciphertext = instream.read(chunk_len)
        if len(ciphertext) < chunk_len:
            raise ValueError("Corrupted backup: unexpected chunk truncation.")

        aad = struct.pack(">Q", chunk_index)
        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
        except Exception as e:
            raise ValueError("Decryption failed. Password may be incorrect, or the backup is corrupted/tampered.") from e

        outstream.write(plaintext)
        chunk_index += 1


def decrypt_and_decompress_stream(instream, outstream, passphrase: str):
    """
    Reads AES-256-GCM chunked encrypted Gzip data from instream, decrypts and verifies GCM tags,
    and decompresses it on-the-fly, writing the raw data to outstream.
    """
    magic = instream.read(8)
    if magic != b"BDRGCMv1":
        raise ValueError("Invalid backup file format or magic bytes mismatch.")

    salt = instream.read(16)
    if len(salt) < 16:
        raise ValueError("Corrupted backup: missing salt.")

    iter_bytes = instream.read(4)
    if len(iter_bytes) < 4:
        raise ValueError("Corrupted backup: missing iterations.")
    iterations = struct.unpack(">I", iter_bytes)[0]

    key = derive_key(passphrase, salt, iterations)
    aesgcm = AESGCM(key)

    # wbits=31 is for gzip decompression compatibility
    decompressor = zlib.decompressobj(wbits=31)

    chunk_index = 0
    while True:
        len_bytes = instream.read(4)
        if len(len_bytes) < 4:
            raise ValueError("Corrupted backup: unexpected EOF while reading chunk length.")
        chunk_len = struct.unpack(">I", len_bytes)[0]

        if chunk_len == 0:
            break

        nonce = instream.read(12)
        if len(nonce) < 12:
            raise ValueError("Corrupted backup: missing nonce.")

        ciphertext = instream.read(chunk_len)
        if len(ciphertext) < chunk_len:
            raise ValueError("Corrupted backup: unexpected chunk truncation.")

        aad = struct.pack(">Q", chunk_index)
        try:
            plaintext_gzip_chunk = aesgcm.decrypt(nonce, ciphertext, aad)
        except Exception as e:
            raise ValueError("Decryption failed. Password may be incorrect, or the backup is corrupted/tampered.") from e

        decompressed_data = decompressor.decompress(plaintext_gzip_chunk)
        if decompressed_data:
            outstream.write(decompressed_data)

        chunk_index += 1

    remaining = decompressor.flush()
    if remaining:
        outstream.write(remaining)
