import jsonschema
from django.core.exceptions import ValidationError


class BaseBlock:
    """
    Abstract base class representing a generic block.
    """

    block_type = None
    schema_version = 1
    purpose = ""
    validation_rules = []
    required_fields = []
    optional_fields = []
    media_dependencies = []
    seo_support = False

    def get_data_schema(self):
        """
        Returns the jsonschema definition for the 'data' payload of the block.
        """
        raise NotImplementedError("Subclasses must implement get_data_schema")

    def validate(self, payload):
        """
        Validates the block dictionary against the envelope and internal data schema.
        """
        # Universal settings object schema
        settings_schema = {
            "type": "object",
            "properties": {
                "align": {"type": "string", "enum": ["left", "center", "right", "justify"]},
                "spacing": {"type": "string", "enum": ["xs", "sm", "md", "lg", "xl", "none"]},
                "theme": {"type": "string"},
                "visibility": {"type": "string", "enum": ["visible", "hidden"]},
                "animation": {"type": "string"},
                "width": {"type": "string", "enum": ["contained", "full_width", "narrow"]},
                "container": {"type": "string"},
                "responsive": {"type": "object"},
                "custom_class": {"type": ["string", "null"]},
                "variant": {"type": "string"},
                "appearance": {"type": "string"},
            },
        }

        # Universal metadata/meta object schema
        meta_schema = {
            "type": "object",
            "properties": {
                "locked": {"type": "boolean"},
                "hidden": {"type": "boolean"},
                "created_by": {"type": ["integer", "null"]},
                "updated_by": {"type": ["integer", "null"]},
                "draft": {"type": "boolean"},
                "deleted": {"type": "boolean"},
                "internal_notes": {"type": "string"},
            },
        }

        # Extract any definitions from the sub-schema to the root of the envelope
        import copy
        data_schema = copy.deepcopy(self.get_data_schema())
        definitions = {}
        if isinstance(data_schema, dict) and "definitions" in data_schema:
            definitions.update(data_schema.pop("definitions"))

        # Define general envelope schema with universal settings and meta objects
        envelope_schema = {
            "type": "object",
            "required": ["id", "type", "version", "order", "data"],
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "type": {"type": "string", "enum": [self.block_type]},
                "version": {"type": "integer", "minimum": 1},
                "order": {"type": "integer"},
                "settings": settings_schema,
                "metadata": meta_schema,
                "meta": meta_schema,
                "data": data_schema,
            },
        }
        if definitions:
            envelope_schema["definitions"] = definitions

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

    def get_seo_metadata(self, data):
        """
        Returns structured SEO metadata for this block if supported.
        """
        return None

    def get_text_content(self, data):
        """
        Returns the raw string content of this block for search or reading time calculation.
        """
        return ""


class HeadingBlock(BaseBlock):
    block_type = "heading"
    purpose = "Structural headings for organizing sections of the article."
    validation_rules = [
        "level must be an integer between 1 and 6",
        "text must be a non-empty string",
    ]
    required_fields = ["level", "text"]
    optional_fields = ["anchor_id"]
    media_dependencies = []
    seo_support = False

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["level", "text"],
            "properties": {
                "level": {"type": "integer", "enum": [1, 2, 3, 4, 5, 6]},
                "text": {"type": "string", "minLength": 1},
                "anchor_id": {"type": "string"},
            },
        }

    def get_text_content(self, data):
        return data.get("text", "")


class ParagraphBlock(BaseBlock):
    block_type = "paragraph"
    purpose = "Structured rich content paragraphs using node arrays to ensure backend has no HTML dependency."
    validation_rules = [
        "content must be an array of structured text node dictionaries",
        "nodes must specify type, optional value, or children nodes",
    ]
    required_fields = ["content"]
    optional_fields = []
    media_dependencies = []
    seo_support = False

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["content"],
            "properties": {
                "content": {
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/paragraph_node"
                    }
                }
            },
            "definitions": {
                "paragraph_node": {
                    "type": "object",
                    "required": ["type"],
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": [
                                "text", "strong", "code", "italic", "underline", "strike",
                                "link", "inline_code", "emoji", "mention", "highlight",
                                "subscript", "superscript", "keyboard", "small", "mark"
                            ]
                        },
                        "value": {"type": "string"},
                        "href": {"type": "string"},
                        "title": {"type": "string"},
                        "children": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/paragraph_node"}
                        }
                    }
                }
            }
        }

    def _is_node_empty(self, node):
        if not isinstance(node, dict):
            return True
        val = node.get("value", "")
        if val and val.strip():
            return False
        for child in node.get("children", []):
            if not self._is_node_empty(child):
                return False
        return True

    def is_empty(self, data):
        content = data.get("content", [])
        if not content:
            return True
        for node in content:
            if not self._is_node_empty(node):
                return False
        return True

    def _get_node_text(self, node):
        if not isinstance(node, dict):
            return ""
        val = node.get("value", "")
        children_text = " ".join([self._get_node_text(child) for child in node.get("children", []) if isinstance(child, dict)])
        return f"{val} {children_text}".strip()

    def get_text_content(self, data):
        nodes = data.get("content", [])
        return " ".join([self._get_node_text(node) for node in nodes if isinstance(node, dict)]).strip()


class ImageBlock(BaseBlock):
    block_type = "image"
    purpose = "Single image referencing a media entity from the media library."
    validation_rules = [
        "media_id must be a valid positive integer referencing an active media",
    ]
    required_fields = ["media_id"]
    optional_fields = ["caption", "alt", "lazy", "link", "target", "object_fit", "focal_point", "loading", "decoding", "fetch_priority", "responsive_behavior"]
    media_dependencies = ["media_id"]
    seo_support = False

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["media_id"],
            "properties": {
                "media_id": {"type": "integer", "minimum": 1},
                "caption": {"type": "string"},
                "alt": {"type": "string"},
                "lazy": {"type": "boolean"},
                "link": {"type": "string"},
                "target": {"type": "string", "enum": ["_blank", "_self"]},
                "object_fit": {"type": "string", "enum": ["contain", "cover", "fill", "none", "scale-down"]},
                "focal_point": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "number"},
                        "y": {"type": "number"}
                    }
                },
                "loading": {"type": "string", "enum": ["lazy", "eager"]},
                "decoding": {"type": "string", "enum": ["async", "sync", "auto"]},
                "fetch_priority": {"type": "string", "enum": ["high", "low", "auto"]},
                "responsive_behavior": {"type": "string"},
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

    def get_text_content(self, data):
        return data.get("caption", "")


class GalleryBlock(BaseBlock):
    block_type = "gallery"
    purpose = "A carousel or grid gallery referencing multiple media library images."
    validation_rules = [
        "media_ids must be an array of positive integers referencing active media items",
    ]
    required_fields = ["media_ids"]
    optional_fields = ["layout", "aspect_ratio"]
    media_dependencies = ["media_ids"]
    seo_support = False

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
    purpose = "Highlighted citation blockquote."
    validation_rules = [
        "text must be a non-empty string",
    ]
    required_fields = ["text"]
    optional_fields = ["citation"]
    media_dependencies = []
    seo_support = False

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["text"],
            "properties": {
                "text": {"type": "string", "minLength": 1},
                "citation": {"type": "string"},
            },
        }

    def get_text_content(self, data):
        return f"{data.get('text', '')} {data.get('citation', '')}".strip()


class TableBlock(BaseBlock):
    block_type = "table"
    purpose = "Tabular data represented completely as structured matrix contracts."
    validation_rules = [
        "headers must be a 1D array of strings",
        "rows must be a 2D array of strings",
    ]
    required_fields = ["headers", "rows"]
    optional_fields = []
    media_dependencies = []
    seo_support = False

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

    def get_text_content(self, data):
        headers_text = " ".join(data.get("headers", []))
        rows_text = " ".join([" ".join(row) for row in data.get("rows", [])])
        return f"{headers_text} {rows_text}".strip()


class CodeBlock(BaseBlock):
    block_type = "code"
    purpose = "Pre-formatted code block indicating target syntax highlighter engine."
    validation_rules = [
        "code must be a non-empty string",
    ]
    required_fields = ["code"]
    optional_fields = ["language", "show_line_numbers"]
    media_dependencies = []
    seo_support = False

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["code"],
            "properties": {
                "code": {"type": "string", "minLength": 1},
                "language": {"type": "string"},
                "show_line_numbers": {"type": "boolean"},
            },
        }

    def get_text_content(self, data):
        return data.get("code", "")


class DividerBlock(BaseBlock):
    block_type = "divider"
    purpose = "Visual content separator/section split contract."
    validation_rules = [
        "style must be one of solid, dashed, dots",
    ]
    required_fields = []
    optional_fields = ["style"]
    media_dependencies = []
    seo_support = False

    def get_data_schema(self):
        return {
            "type": "object",
            "properties": {
                "style": {"type": "string", "enum": ["solid", "dashed", "dots"]}
            },
        }


class VideoBlock(BaseBlock):
    block_type = "video"
    purpose = "Embedded video component support both local and external providers."
    validation_rules = [
        "provider must be local, youtube, or vimeo",
        "either media_id or external_url must be specified",
    ]
    required_fields = []
    optional_fields = ["media_id", "provider", "external_url", "autoplay", "controls"]
    media_dependencies = ["media_id"]
    seo_support = True

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

    def get_seo_metadata(self, data):
        url = data.get("external_url", "")
        if data.get("media_id") and "media" in data:
            url = data["media"].get("url", url)
        return {
            "@context": "https://schema.org",
            "@type": "VideoObject",
            "name": f"Video ({data.get('provider', 'local')})",
            "contentUrl": url,
        }


class EmbedBlock(BaseBlock):
    block_type = "embed"
    purpose = "Integrate external rich entities (like social media profiles or tweets) via custom adapters."
    validation_rules = [
        "url must be a valid format",
        "embed_type must be one of twitter, instagram, iframe",
    ]
    required_fields = ["url"]
    optional_fields = ["embed_type", "width", "height"]
    media_dependencies = []
    seo_support = False

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
    purpose = "Interactive Call-To-Action (CTA) link."
    validation_rules = [
        "label must be a non-empty string",
        "url must be a valid target link",
        "target must be _blank or _self",
    ]
    required_fields = ["label", "url"]
    optional_fields = ["target", "style_preset"]
    media_dependencies = []
    seo_support = False

    def get_data_schema(self):
        return {
            "type": "object",
            "required": ["label", "url"],
            "properties": {
                "label": {"type": "string", "minLength": 1},
                "url": {"type": "string"},
                "target": {"type": "string", "enum": ["_blank", "_self"]},
                "style_preset": {"type": "string"},
            },
        }

    def get_text_content(self, data):
        return data.get("label", "")


class AccordionBlock(BaseBlock):
    block_type = "accordion"
    purpose = "Interactive accordion panels of headers and content blocks."
    validation_rules = [
        "items must be an array of objects containing title and content text fields",
    ]
    required_fields = ["items"]
    optional_fields = []
    media_dependencies = []
    seo_support = False

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
                            "title": {"type": "string", "minLength": 1},
                            "content": {"type": "string"},
                        },
                    },
                }
            },
        }

    def get_text_content(self, data):
        items = data.get("items", [])
        return " ".join(
            [f"{i.get('title', '')} {i.get('content', '')}" for i in items]
        ).strip()


class FAQBlock(BaseBlock):
    block_type = "faq"
    purpose = (
        "Collapsible FAQ section conforming strictly to SEO Rich Snippet requirements."
    )
    validation_rules = [
        "questions must be an array of objects specifying q and a text fields",
    ]
    required_fields = ["questions"]
    optional_fields = []
    media_dependencies = []
    seo_support = True

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
                            "q": {"type": "string", "minLength": 1},
                            "a": {"type": "string", "minLength": 1},
                        },
                    },
                }
            },
        }

    def get_text_content(self, data):
        questions = data.get("questions", [])
        return " ".join(
            [f"{q.get('q', '')} {q.get('a', '')}" for q in questions]
        ).strip()

    def get_seo_metadata(self, data):
        return {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": item.get("q", ""),
                    "acceptedAnswer": {"@type": "Answer", "text": item.get("a", "")},
                }
                for item in data.get("questions", [])
            ],
        }


class TimelineBlock(BaseBlock):
    block_type = "timeline"
    purpose = "Visual chronological events stream contract."
    validation_rules = [
        "events must be an array of objects specifying date and title values",
    ]
    required_fields = ["events"]
    optional_fields = []
    media_dependencies = []
    seo_support = False

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
                            "date": {"type": "string", "minLength": 1},
                            "title": {"type": "string", "minLength": 1},
                            "description": {"type": "string"},
                        },
                    },
                }
            },
        }

    def get_text_content(self, data):
        events = data.get("events", [])
        return " ".join(
            [
                f"{e.get('date', '')} {e.get('title', '')} {e.get('description', '')}"
                for e in events
            ]
        ).strip()


class RelatedArticlesBlock(BaseBlock):
    block_type = "related_articles"
    purpose = "Reference related articles by ID for rendering dynamically."
    validation_rules = [
        "article_ids must be an array of integers",
    ]
    required_fields = ["article_ids"]
    optional_fields = []
    media_dependencies = []
    seo_support = False

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

    def get_all_definitions(self):
        """
        EN: Returns complete headless contract metadata for all registered block types.
        """
        definitions = []
        for name, instance in self._registry.items():
            definitions.append(
                {
                    "type": instance.block_type,
                    "version": instance.schema_version,
                    "purpose": instance.purpose,
                    "required_fields": instance.required_fields,
                    "optional_fields": instance.optional_fields,
                    "validation_rules": instance.validation_rules,
                    "media_dependencies": instance.media_dependencies,
                    "seo_support": instance.seo_support,
                    "schema": instance.get_data_schema(),
                }
            )
        return definitions

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
