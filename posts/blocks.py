import jsonschema
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError


class BaseBlock:
    """
    Abstract base class representing a generic block.
    """

    block_type = None
    schema_version = 1

    def get_data_schema(self):
        """
        Returns the jsonschema definition for the 'data' payload of the block.
        """
        raise NotImplementedError("Subclasses must implement get_data_schema")

    def validate(self, payload):
        """
        Validates the block dictionary against the envelope and internal data schema.
        """
        # Define general envelope schema
        envelope_schema = {
            "type": "object",
            "required": ["id", "type", "version", "order", "data"],
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "type": {"type": "string", "enum": [self.block_type]},
                "version": {"type": "integer", "minimum": 1},
                "order": {"type": "integer"},
                "settings": {"type": "object"},
                "metadata": {"type": "object"},
                "data": self.get_data_schema(),
            },
        }
        try:
            jsonschema.validate(instance=payload, schema=envelope_schema)
        except jsonschema.exceptions.ValidationError as e:
            # Format the error nicely
            parts = [str(p) for p in e.path]
            formatted_parts = []
            for p in parts:
                if p.isdigit():
                    formatted_parts.append(f"[{p}]")
                else:
                    formatted_parts.append(f".{p}")
            suffix = "".join(formatted_parts)
            field_name = f"content_blocks{suffix}"
            raise ValidationError({field_name: e.message})

    def get_referenced_media_ids(self, data):
        """
        Returns a set of media IDs referenced within this block.
        """
        return set()

    def is_empty(self, data):
        """
        Returns True if the block is considered empty/invalid content.
        """
        return False

    def expand_media_references(self, data, media_map):
        """
        Mutates data in-place to expand/inject media object representations.
        """
        pass


class HeadingBlock(BaseBlock):
    block_type = "heading"

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["level", "text"],
            "properties": {
                "level": {"type": "integer", "enum": [1, 2, 3, 4, 5, 6]},
                "text": {"type": "string"},
                "anchor_id": {"type": "string"},
            },
        }


class ParagraphBlock(BaseBlock):
    block_type = "paragraph"

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["text"],
            "properties": {"text": {"type": "string"}},
        }

    def is_empty(self, data):
        text = data.get("text", "").strip()
        clean_text = BeautifulSoup(text, "html.parser").get_text().strip()
        return not clean_text


class ImageBlock(BaseBlock):
    block_type = "image"

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["media_id"],
            "properties": {
                "media_id": {"type": "integer", "minimum": 1},
                "caption": {"type": "string"},
                "alt": {"type": "string"},
                "lazy": {"type": "boolean"},
            },
        }

    def get_referenced_media_ids(self, data):
        media_id = data.get("media_id")
        return {media_id} if media_id else set()

    def is_empty(self, data):
        return not data.get("media_id")

    def expand_media_references(self, data, media_map):
        media_id = data.get("media_id")
        if media_id in media_map:
            data["media"] = media_map[media_id]


class GalleryBlock(BaseBlock):
    block_type = "gallery"

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["media_ids"],
            "properties": {
                "media_ids": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 1},
                },
                "layout": {"type": "string", "enum": ["grid", "slider"]},
                "aspect_ratio": {"type": "string"},
            },
        }

    def get_referenced_media_ids(self, data):
        return set(data.get("media_ids", []))

    def expand_media_references(self, data, media_map):
        media_ids = data.get("media_ids", [])
        data["medias"] = [media_map[mid] for mid in media_ids if mid in media_map]


class QuoteBlock(BaseBlock):
    block_type = "quote"

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["text"],
            "properties": {"text": {"type": "string"}, "citation": {"type": "string"}},
        }


class TableBlock(BaseBlock):
    block_type = "table"

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["headers", "rows"],
            "properties": {
                "headers": {"type": "array", "items": {"type": "string"}},
                "rows": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "string"}},
                },
            },
        }


class CodeBlock(BaseBlock):
    block_type = "code"

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["code"],
            "properties": {
                "code": {"type": "string"},
                "language": {"type": "string"},
                "show_line_numbers": {"type": "boolean"},
            },
        }


class DividerBlock(BaseBlock):
    block_type = "divider"

    def get_data_schema(self):
        return {
            "type": "object",
            "properties": {
                "style": {"type": "string", "enum": ["solid", "dashed", "dots"]}
            },
        }


class VideoBlock(BaseBlock):
    block_type = "video"

    def get_data_schema(self):
        return {
            "type": "object",
            "properties": {
                "media_id": {"type": "integer", "minimum": 1},
                "provider": {"type": "string", "enum": ["local", "youtube", "vimeo"]},
                "external_url": {"type": "string"},
                "autoplay": {"type": "boolean"},
                "controls": {"type": "boolean"},
            },
        }

    def get_referenced_media_ids(self, data):
        media_id = data.get("media_id")
        return {media_id} if media_id else set()

    def expand_media_references(self, data, media_map):
        media_id = data.get("media_id")
        if media_id in media_map:
            data["media"] = media_map[media_id]


class EmbedBlock(BaseBlock):
    block_type = "embed"

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {"type": "string"},
                "embed_type": {
                    "type": "string",
                    "enum": ["twitter", "instagram", "iframe"],
                },
                "width": {"type": "integer"},
                "height": {"type": "integer"},
            },
        }


class ButtonBlock(BaseBlock):
    block_type = "button"

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["label", "url"],
            "properties": {
                "label": {"type": "string"},
                "url": {"type": "string"},
                "target": {"type": "string", "enum": ["_blank", "_self"]},
                "style_preset": {"type": "string"},
            },
        }


class AccordionBlock(BaseBlock):
    block_type = "accordion"

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["items"],
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["title", "content"],
                        "properties": {
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                        },
                    },
                }
            },
        }


class FAQBlock(BaseBlock):
    block_type = "faq"

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["questions"],
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["q", "a"],
                        "properties": {
                            "q": {"type": "string"},
                            "a": {"type": "string"},
                        },
                    },
                }
            },
        }


class TimelineBlock(BaseBlock):
    block_type = "timeline"

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["events"],
            "properties": {
                "events": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["date", "title"],
                        "properties": {
                            "date": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                        },
                    },
                }
            },
        }


class RelatedArticlesBlock(BaseBlock):
    block_type = "related_articles"

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["article_ids"],
            "properties": {
                "article_ids": {"type": "array", "items": {"type": "integer"}}
            },
        }


class BlockRegistry:
    """
    Central registry to mount, validate, and access blocks.
    """

    def __init__(self):
        self._registry = {}
        self.register(HeadingBlock())
        self.register(ParagraphBlock())
        self.register(ImageBlock())
        self.register(GalleryBlock())
        self.register(QuoteBlock())
        self.register(TableBlock())
        self.register(CodeBlock())
        self.register(DividerBlock())
        self.register(VideoBlock())
        self.register(EmbedBlock())
        self.register(ButtonBlock())
        self.register(AccordionBlock())
        self.register(FAQBlock())
        self.register(TimelineBlock())
        self.register(RelatedArticlesBlock())

    def register(self, block_instance):
        self._registry[block_instance.block_type] = block_instance

    def get_block(self, block_type):
        return self._registry.get(block_type)

    def validate_block_payload(self, block_payload):
        """
        Validates a single block payload structure and delegate schema check to block type.
        """
        if not isinstance(block_payload, dict):
            raise ValidationError(
                {"content_blocks": "Block payload must be a dictionary."}
            )

        block_type = block_payload.get("type")
        if not block_type:
            raise ValidationError({"content_blocks.type": "Block type is required."})

        handler = self.get_block(block_type)
        if not handler:
            raise ValidationError(
                {"content_blocks.type": f"Unsupported block type: '{block_type}'."}
            )

        # Check version mismatches
        version = block_payload.get("version")
        if version is not None and version > handler.schema_version:
            raise ValidationError(
                {
                    "content_blocks.version": f"Unsupported block version: {version} for type '{block_type}'."
                }
            )

        handler.validate(block_payload)


# Global singleton registry
block_registry = BlockRegistry()
