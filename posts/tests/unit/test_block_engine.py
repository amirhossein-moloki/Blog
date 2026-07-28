from django.core.exceptions import ValidationError
from django.test import TestCase

from medias.models import ArticleMedia, Media
from posts.factories import ArticleFactory
from posts.serializers import ArticleCreateUpdateSerializer, ArticleDetailSerializer
from posts.services import (
    calculate_blocks_reading_time,
    validate_and_sanitize_blocks,
)


class BlockEngineUnitTests(TestCase):
    def setUp(self):
        # Create some media for validation tests
        self.media1 = Media.objects.create(
            storage_key="img1.jpg",
            url="/media/img1.jpg",
            type="image",
            mime="image/jpeg",
            is_active=True,
        )
        self.media2 = Media.objects.create(
            storage_key="img2.jpg",
            url="/media/img2.jpg",
            type="image",
            mime="image/jpeg",
            is_active=True,
        )

    def test_valid_blocks_validation_and_normalization(self):
        blocks = [
            {
                "id": "blk_1",
                "type": "heading",
                "version": 1,
                "order": 5,
                "data": {"level": 2, "text": "Header 2 Text"},
            },
            {
                "id": "blk_2",
                "type": "paragraph",
                "version": 1,
                "order": 12,
                "data": {
                    "text": "<p>Some text and <script>alert(1)</script> <strong>bold</strong></p>"
                },
            },
            {
                "id": "blk_3",
                "type": "image",
                "version": 1,
                "order": 2,
                "data": {"media_id": self.media1.id, "caption": "My Image Caption"},
            },
        ]

        # Valid blocks should validate and have normalized orders (1, 2, 3)
        normalized = validate_and_sanitize_blocks(blocks)
        self.assertEqual(len(normalized), 3)
        self.assertEqual(
            normalized[0]["id"], "blk_3"
        )  # order 2 -> first (will get normalized to order 1)
        self.assertEqual(normalized[0]["order"], 1)
        self.assertEqual(
            normalized[1]["id"], "blk_1"
        )  # order 5 -> second (normalized to 2)
        self.assertEqual(normalized[1]["order"], 2)
        self.assertEqual(
            normalized[2]["id"], "blk_2"
        )  # order 12 -> third (normalized to 3)
        self.assertEqual(normalized[2]["order"], 3)

        # HTML sanitization: <script> tags must be stripped, but safe formatting like strong kept
        self.assertNotIn("script", normalized[2]["data"]["text"])
        self.assertIn("<strong>", normalized[2]["data"]["text"])

    def test_all_block_types_schemas(self):
        # We test a large array containing valid data for every single block type in the registry
        blocks = [
            {
                "id": "b1",
                "type": "heading",
                "version": 1,
                "order": 1,
                "data": {"level": 1, "text": "H1 title", "anchor_id": "anc1"},
            },
            {
                "id": "b2",
                "type": "paragraph",
                "version": 1,
                "order": 2,
                "data": {"text": "hello paragraph"},
            },
            {
                "id": "b3",
                "type": "image",
                "version": 1,
                "order": 3,
                "data": {
                    "media_id": self.media1.id,
                    "caption": "cap",
                    "alt": "alt text",
                    "lazy": True,
                },
            },
            {
                "id": "b4",
                "type": "gallery",
                "version": 1,
                "order": 4,
                "data": {
                    "media_ids": [self.media1.id, self.media2.id],
                    "layout": "grid",
                    "aspect_ratio": "16:9",
                },
            },
            {
                "id": "b5",
                "type": "quote",
                "version": 1,
                "order": 5,
                "data": {"text": "wise quote", "citation": "Aristotle"},
            },
            {
                "id": "b6",
                "type": "table",
                "version": 1,
                "order": 6,
                "data": {
                    "headers": ["h1", "h2"],
                    "rows": [["r1c1", "r1c2"], ["r2c1", "r2c2"]],
                },
            },
            {
                "id": "b7",
                "type": "code",
                "version": 1,
                "order": 7,
                "data": {
                    "code": "print('ok')",
                    "language": "python",
                    "show_line_numbers": True,
                },
            },
            {
                "id": "b8",
                "type": "divider",
                "version": 1,
                "order": 8,
                "data": {"style": "solid"},
            },
            {
                "id": "b9",
                "type": "video",
                "version": 1,
                "order": 9,
                "data": {
                    "media_id": self.media1.id,
                    "provider": "local",
                    "external_url": "url",
                    "autoplay": False,
                    "controls": True,
                },
            },
            {
                "id": "b10",
                "type": "embed",
                "version": 1,
                "order": 10,
                "data": {
                    "url": "https://twitter.com",
                    "embed_type": "twitter",
                    "width": 600,
                    "height": 400,
                },
            },
            {
                "id": "b11",
                "type": "button",
                "version": 1,
                "order": 11,
                "data": {
                    "label": "Click me",
                    "url": "https://google.com",
                    "target": "_blank",
                    "style_preset": "primary",
                },
            },
            {
                "id": "b12",
                "type": "accordion",
                "version": 1,
                "order": 12,
                "data": {"items": [{"title": "Q1", "content": "A1"}]},
            },
            {
                "id": "b13",
                "type": "faq",
                "version": 1,
                "order": 13,
                "data": {"questions": [{"q": "Q?", "a": "A!"}]},
            },
            {
                "id": "b14",
                "type": "timeline",
                "version": 1,
                "order": 14,
                "data": {
                    "events": [
                        {"date": "2026", "title": "Milestone", "description": "desc"}
                    ]
                },
            },
            {
                "id": "b15",
                "type": "related_articles",
                "version": 1,
                "order": 15,
                "data": {"article_ids": [1, 2, 3]},
            },
        ]
        # Full validation and normalization must pass cleanly
        normalized = validate_and_sanitize_blocks(blocks)
        self.assertEqual(len(normalized), 15)

    def test_invalid_block_type_raises_error(self):
        blocks = [
            {
                "id": "blk_1",
                "type": "nonexistent_block_type",
                "version": 1,
                "order": 1,
                "data": {},
            }
        ]
        with self.assertRaises(ValidationError) as ctx:
            validate_and_sanitize_blocks(blocks)
        self.assertIn("Unsupported block type", str(ctx.exception))

    def test_invalid_schema_version_raises_error(self):
        blocks = [
            {
                "id": "blk_1",
                "type": "paragraph",
                "version": 99,
                "order": 1,
                "data": {"text": "hello"},
            }
        ]
        with self.assertRaises(ValidationError) as ctx:
            validate_and_sanitize_blocks(blocks)
        self.assertIn("Unsupported block version", str(ctx.exception))

    def test_duplicate_block_id_raises_error(self):
        blocks = [
            {
                "id": "blk_1",
                "type": "paragraph",
                "version": 1,
                "order": 1,
                "data": {"text": "hello"},
            },
            {
                "id": "blk_1",
                "type": "paragraph",
                "version": 1,
                "order": 2,
                "data": {"text": "world"},
            },
        ]
        with self.assertRaises(ValidationError) as ctx:
            validate_and_sanitize_blocks(blocks)
        self.assertIn("Duplicate block ID detected", str(ctx.exception))

    def test_duplicate_block_order_raises_error(self):
        blocks = [
            {
                "id": "blk_1",
                "type": "paragraph",
                "version": 1,
                "order": 1,
                "data": {"text": "hello"},
            },
            {
                "id": "blk_2",
                "type": "paragraph",
                "version": 1,
                "order": 1,
                "data": {"text": "world"},
            },
        ]
        with self.assertRaises(ValidationError) as ctx:
            validate_and_sanitize_blocks(blocks)
        self.assertIn("Duplicate block order detected", str(ctx.exception))

    def test_missing_media_id_raises_error(self):
        blocks = [
            {
                "id": "blk_1",
                "type": "image",
                "version": 1,
                "order": 1,
                "data": {"media_id": 99999, "caption": "test"},  # non-existent ID
            }
        ]
        with self.assertRaises(ValidationError) as ctx:
            validate_and_sanitize_blocks(blocks, language_code="en")
        self.assertIn("content_blocks[0].data.media_id", ctx.exception.message_dict)
        self.assertIn(
            "Media with ID 99999 does not exist",
            ctx.exception.message_dict["content_blocks[0].data.media_id"][0],
        )

        # Persian response check
        with self.assertRaises(ValidationError) as ctx:
            validate_and_sanitize_blocks(blocks, language_code="fa")
        self.assertIn("content_blocks[0].data.media_id", ctx.exception.message_dict)
        self.assertIn(
            "رسانه‌ای با شناسه 99999 در کتابخانه رسانه‌ها وجود ندارد.",
            ctx.exception.message_dict["content_blocks[0].data.media_id"][0],
        )

    def test_empty_paragraph_block_raises_error(self):
        blocks = [
            {
                "id": "blk_1",
                "type": "paragraph",
                "version": 1,
                "order": 1,
                "data": {"text": "   <p> </p>  "},
            }
        ]
        with self.assertRaises(ValidationError) as ctx:
            validate_and_sanitize_blocks(blocks)
        self.assertIn("Empty paragraph blocks are not allowed", str(ctx.exception))

    def test_heading_hierarchy_violation_raises_error(self):
        blocks = [
            {
                "id": "blk_1",
                "type": "heading",
                "version": 1,
                "order": 1,
                "data": {
                    "level": 3,  # jumping straight to H3 is forbidden without preceding H2
                    "text": "Heading 3",
                },
            }
        ]
        with self.assertRaises(ValidationError) as ctx:
            validate_and_sanitize_blocks(blocks)
        self.assertIn("Heading hierarchy violation", str(ctx.exception))

    def test_reading_time_calculation_for_blocks(self):
        blocks = [
            {
                "id": "blk_1",
                "type": "heading",
                "version": 1,
                "order": 1,
                "data": {"level": 2, "text": "word " * 100},
            },
            {
                "id": "blk_2",
                "type": "paragraph",
                "version": 1,
                "order": 2,
                "data": {"text": "word " * 100},
            },
        ]
        # 200 words = 1 minute (60 seconds)
        reading_time = calculate_blocks_reading_time(blocks)
        self.assertEqual(reading_time, 60)


class BlockEngineIntegrationTests(TestCase):
    def setUp(self):
        self.article = ArticleFactory()
        self.author = self.article.author
        self.media1 = Media.objects.create(
            storage_key="test-block.jpg",
            url="/media/test-block.jpg",
            type="image",
            mime="image/jpeg",
            is_active=True,
        )

    def test_create_article_with_blocks_via_serializer(self):
        data = {
            "title": "New Block Article",
            "excerpt": "My excerpt",
            "content": "",
            "content_blocks": [
                {
                    "id": "blk_h1",
                    "type": "heading",
                    "version": 1,
                    "order": 1,
                    "data": {"level": 2, "text": "H2 Heading"},
                },
                {
                    "id": "blk_img",
                    "type": "image",
                    "version": 1,
                    "order": 2,
                    "data": {"media_id": self.media1.id, "caption": "My caption"},
                },
            ],
        }
        # Create through serializer
        serializer = ArticleCreateUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        article = serializer.save(author=self.author)

        # Verify content_blocks are persisted
        trans = article.translation
        self.assertEqual(len(trans.content_blocks), 2)
        self.assertEqual(trans.content_blocks[1]["id"], "blk_img")

        # Verify that Media is synced with ArticleMedia
        self.assertTrue(
            ArticleMedia.objects.filter(
                article=article, media=self.media1, attachment_type="in-content"
            ).exists()
        )

    def test_detail_serializer_expands_media(self):
        trans = self.article.translation
        trans.content_blocks = [
            {
                "id": "blk_img",
                "type": "image",
                "version": 1,
                "order": 1,
                "data": {"media_id": self.media1.id, "caption": "prefetted"},
            }
        ]
        trans.save()

        # Retrieve through ArticleDetailSerializer
        serializer = ArticleDetailSerializer(self.article)
        repr_data = serializer.data
        blocks = repr_data["content_blocks"]

        # Verify block has expanded 'media' representation
        self.assertEqual(len(blocks), 1)
        media_expanded = blocks[0]["data"]["media"]
        self.assertIsNotNone(media_expanded)
        self.assertEqual(media_expanded["id"], self.media1.id)
        self.assertEqual(media_expanded["url"], self.media1.url)
