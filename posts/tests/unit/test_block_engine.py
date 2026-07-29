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
                    "content": [
                        {
                            "type": "text",
                            "value": "Some text and <script>alert(1)</script> <strong>bold</strong>",
                        }
                    ]
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
        self.assertNotIn("script", normalized[2]["data"]["content"][0]["value"])
        self.assertIn("<strong>", normalized[2]["data"]["content"][0]["value"])

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
                "data": {"content": [{"type": "text", "value": "hello paragraph"}]},
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
                    "title": "Timeline of Construction",
                    "orientation": "vertical",
                    "events": [
                        {
                            "id": "ev_1",
                            "date": {"type": "year", "value": "1300"},
                            "title": "Build",
                            "description": "desc",
                            "media_id": self.media1.id,
                            "metadata": {"location": "Tabriz", "category": "heritage"},
                        }
                    ],
                },
            },
            {
                "id": "b15",
                "type": "location",
                "version": 1,
                "order": 15,
                "data": {
                    "title": "Alavi House",
                    "description": "Historical building",
                    "address": {
                        "country": "Iran",
                        "province": "East Azerbaijan",
                        "city": "Tabriz",
                        "street": "Alavi Alley",
                    },
                    "coordinates": {"latitude": 38.08, "longitude": 46.29},
                    "geo": {"type": "Point", "coordinates": [46.29, 38.08]},
                    "contact": {
                        "phone": "123456",
                        "website": "http://alavi.com",
                        "email": None,
                    },
                    "opening_hours": [
                        {"day": "saturday", "open": "09:00", "close": "17:00"}
                    ],
                    "map": {"provider": "google", "zoom": 15},
                    "media_id": self.media2.id,
                },
            },
            {
                "id": "b16",
                "type": "related_articles",
                "version": 1,
                "order": 16,
                "data": {"article_ids": [1, 2, 3]},
            },
        ]
        # Full validation and normalization must pass cleanly
        normalized = validate_and_sanitize_blocks(blocks)
        self.assertEqual(len(normalized), 16)

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
                "data": {"content": [{"type": "text", "value": "hello"}]},
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
                "data": {"content": [{"type": "text", "value": "hello"}]},
            },
            {
                "id": "blk_1",
                "type": "paragraph",
                "version": 1,
                "order": 2,
                "data": {"content": [{"type": "text", "value": "world"}]},
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
                "data": {"content": [{"type": "text", "value": "hello"}]},
            },
            {
                "id": "blk_2",
                "type": "paragraph",
                "version": 1,
                "order": 1,
                "data": {"content": [{"type": "text", "value": "world"}]},
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
                "data": {"content": [{"type": "text", "value": "   "}]},
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
                "data": {"content": [{"type": "text", "value": "word " * 100}]},
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

    def test_presentation_agnostic_headless_attributes(self):
        trans = self.article.translation
        trans.content_blocks = [
            {
                "id": "blk_p1",
                "type": "paragraph",
                "version": 1,
                "order": 1,
                "data": {"content": [{"type": "text", "value": "A paragraph text"}]},
            },
            {
                "id": "blk_faq1",
                "type": "faq",
                "version": 1,
                "order": 2,
                "data": {"questions": [{"q": "Question 1?", "a": "Answer 1!"}]},
            },
        ]
        trans.save()

        serializer = ArticleDetailSerializer(self.article)
        repr_data = serializer.data

        # 1. Blocks alias verification
        self.assertIn("blocks", repr_data)
        self.assertEqual(repr_data["blocks"], repr_data["content_blocks"])

        blocks = repr_data["blocks"]
        self.assertEqual(len(blocks), 2)

        # 2. Frontend Component Name must be COMPLETELY REMOVED
        self.assertNotIn("component", blocks[0])
        self.assertNotIn("component", blocks[1])

        # 3. Block-level SEO must be COMPLETELY REMOVED
        self.assertNotIn("seo", blocks[0])
        self.assertNotIn("seo", blocks[1])

        # 4. Universal Settings Object must exist on ALL blocks (with default presentation properties)
        for block in blocks:
            self.assertIn("settings", block)
            self.assertEqual(block["settings"]["align"], "left")
            self.assertEqual(block["settings"]["spacing"], "md")

        # 5. Universal Meta Object must exist on ALL blocks
        for block in blocks:
            self.assertIn("meta", block)
            self.assertEqual(block["meta"]["locked"], False)

        # 6. Structured data must be aggregated at the article level
        self.assertIn("structured_data", repr_data)
        self.assertEqual(len(repr_data["structured_data"]), 1)
        self.assertEqual(repr_data["structured_data"][0]["@type"], "FAQPage")
        self.assertEqual(
            repr_data["structured_data"][0]["@context"], "https://schema.org"
        )

        # 7. Article Schema Version must be present
        self.assertEqual(repr_data["article_schema_version"], 2)

    def test_location_and_timeline_blocks_integration(self):
        # Create an article with location and timeline blocks
        trans = self.article.translation
        trans.content_blocks = [
            {
                "id": "blk_loc",
                "type": "location",
                "version": 1,
                "order": 1,
                "data": {
                    "title": "Tabriz Alavi House",
                    "description": "A beautiful historical house",
                    "address": {
                        "country": "Iran",
                        "province": "East Azerbaijan",
                        "city": "Tabriz",
                        "street": "Shams Street",
                    },
                    "coordinates": {"latitude": 38.08, "longitude": 46.29},
                    "geo": {"type": "Point", "coordinates": [46.29, 38.08]},
                    "contact": {"phone": "987654", "website": None, "email": None},
                    "opening_hours": [
                        {"day": "saturday", "open": "08:00", "close": "18:00"}
                    ],
                    "map": {"provider": "google", "zoom": 16},
                    "media_id": self.media1.id,
                },
            },
            {
                "id": "blk_timeline",
                "type": "timeline",
                "version": 1,
                "order": 2,
                "data": {
                    "title": "History of Alavi House",
                    "orientation": "vertical",
                    "events": [
                        {
                            "id": "ev_2",
                            "date": {"type": "year", "value": "1381"},
                            "title": "Heritage Registration",
                            "description": "Registered as national heritage",
                            "media_id": None,
                            "metadata": {"category": "heritage"},
                        },
                        {
                            "id": "ev_1",
                            "date": {"type": "year", "value": "1300"},
                            "title": "Construction",
                            "description": "Constructed in Qajar era",
                            "media_id": self.media1.id,
                            "metadata": {
                                "location": "Tabriz",
                                "category": "construction",
                            },
                        },
                    ],
                },
            },
        ]
        trans.save()

        # Retrieve article details using DetailSerializer
        serializer = ArticleDetailSerializer(self.article)
        repr_data = serializer.data

        blocks = repr_data["content_blocks"]
        self.assertEqual(len(blocks), 2)

        # 1. Location block checks
        loc_block = blocks[0]
        self.assertEqual(loc_block["type"], "location")
        self.assertEqual(loc_block["data"]["title"], "Tabriz Alavi House")
        # Ensure media expansion works for location block
        self.assertIn("media", loc_block["data"])
        self.assertEqual(loc_block["data"]["media"]["id"], self.media1.id)

        # 2. Timeline block checks
        timeline_block = blocks[1]
        self.assertEqual(timeline_block["type"], "timeline")
        self.assertEqual(timeline_block["data"]["title"], "History of Alavi House")

        # Ensure events are chronological-sorted (Construction 1300 first, Heritage Registration 1381 second)
        events = timeline_block["data"]["events"]
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["id"], "ev_1")
        self.assertEqual(events[0]["title"], "Construction")
        # Ensure media expansion works inside timeline events
        self.assertIn("media", events[0])
        self.assertEqual(events[0]["media"]["id"], self.media1.id)

        self.assertEqual(events[1]["id"], "ev_2")
        self.assertEqual(events[1]["title"], "Heritage Registration")
        self.assertNotIn("media", events[1])

        # 3. Structured Data JSON-LD checks
        structured_data = repr_data["structured_data"]
        # Location block generates 1 Place object, Timeline block generates 2 Event objects
        self.assertEqual(len(structured_data), 3)

        # Check Place representation
        place_ld = [item for item in structured_data if item["@type"] == "Place"][0]
        self.assertEqual(place_ld["name"], "Tabriz Alavi House")
        self.assertEqual(place_ld["address"]["addressLocality"], "Tabriz")
        self.assertEqual(place_ld["geo"]["latitude"], 38.08)

        # Check Event representations
        event_lds = [item for item in structured_data if item["@type"] == "Event"]
        self.assertEqual(len(event_lds), 2)

        # Chronological sorting affects blocks list, structured data extraction follows normalized block order
        self.assertEqual(event_lds[0]["name"], "Construction")
        self.assertEqual(event_lds[0]["startDate"], "1300")
        self.assertEqual(event_lds[0]["location"]["name"], "Tabriz")

        self.assertEqual(event_lds[1]["name"], "Heritage Registration")
        self.assertEqual(event_lds[1]["startDate"], "1381")
