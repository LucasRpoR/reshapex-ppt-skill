#!/usr/bin/env python3
"""ReshapeX MCP Server — creates Google Slides presentations using the ReshapeX template.

- ALL text in every element is replaced with user content.
- Slides 2-5 are optional: unused slides are deleted from the copy.
- Footer page numbers update automatically to reflect the actual slide count.
- Visual formatting (colors, fonts, shapes) comes from the template.
"""

import asyncio
from pathlib import Path

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive",
]

TEMPLATE_ID = "1x5583O8UIG9TbNXyyRpXuHz91UzqCNkW-gMJvQu7MZc"
CONFIG_DIR = Path.home() / ".config" / "reshapex-mcp"
TOKEN_FILE = CONFIG_DIR / "token.json"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"

# Element role sequences per slide — sorted by (y, x) position in the template.
# None = skip (reshapex.com branding stays as-is).
# "footer" = page number badge — replaced with "# N of M" automatically.

SLIDE_1_SEQ = [
    "main_title",       # y=7.4  x=4.6
    "client_name",      # y=8.0  x=27.9
    "subtitle_label",   # y=10.0 x=4.6
    "subtitle_desc",    # y=12.3 x=5.6
    "badge",            # y=17.9 x=1.4
    None,               # y=17.9 x=27.4  www.reshapex.com — keep
]

# Slide 2: 3x2 card grid (6 cards max)
SLIDE_2_SEQ = [
    "section_label",
    "tagline_1",
    "tagline_2",
    "sub_desc",
    "card.0.title", "card.1.title", "card.2.title",
    "card.0.badge", "card.1.badge", "card.2.badge",
    "card.0.desc",  "card.1.desc",  "card.2.desc",
    "card.0.details","card.1.details","card.2.details",
    "card.3.title", "card.4.title", "card.5.title",
    "card.3.badge", "card.4.badge", "card.5.badge",
    "card.3.desc",  "card.4.desc",  "card.5.desc",
    "card.3.details","card.4.details","card.5.details",
    "footer",
    None,  # reshapex.com
]

# Slide 3: 3x2 icon-item grid (6 items max)
SLIDE_3_SEQ = [
    "section_label",
    "tagline_1",
    "tagline_2",
    "sub_desc",
    "item.0.icon","item.0.title","item.1.icon","item.1.title",
    "item.2.icon","item.2.title",
    "item.0.desc", "item.1.desc", "item.2.desc",
    "item.0.source","item.1.source","item.2.source",
    "item.3.icon","item.3.title","item.4.icon","item.4.title",
    "item.5.icon","item.5.title",
    "item.3.desc", "item.4.desc", "item.5.desc",
    "item.3.source","item.4.source","item.5.source",
    "footer",
    None,  # reshapex.com
]

# Slide 4: 2x2 numbered asks (4 asks max)
# Col-1 asks (indices 0, 2) have an "example" element; col-2 (indices 1, 3) do not.
SLIDE_4_SEQ = [
    "section_label",
    "tagline_1",
    "tagline_2",
    "sub_desc",
    "ask.0.num","ask.0.title","ask.1.num","ask.1.title",
    "ask.0.desc","ask.1.desc",
    "ask.0.example",
    "ask.0.unlocks","ask.1.unlocks",
    "ask.2.num","ask.2.title","ask.3.num","ask.3.title",
    "ask.2.desc","ask.3.desc",
    "ask.2.example",
    "ask.2.unlocks","ask.3.unlocks",
    "footer",
    None,  # reshapex.com
]

# Slide 5: 2-column week blocks (2 weeks)
SLIDE_5_SEQ = [
    "section_label",
    "tagline_1",
    "tagline_2",
    "sub_desc",
    "week.0.label","week.1.label",
    "week.0.phase","week.1.phase",
    "week.0.title","week.1.title",
    "week.0.desc", "week.1.desc",
    "week.0.bullets","week.1.bullets",
    "footer",
    None,  # reshapex.com
]

SLIDE_SEQUENCES = [SLIDE_1_SEQ, SLIDE_2_SEQ, SLIDE_3_SEQ, SLIDE_4_SEQ, SLIDE_5_SEQ]

app = Server("reshapex-mcp")


def authenticate() -> Credentials:
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(creds.to_json())
    return creds


def get_services():
    creds = authenticate()
    return (
        build("slides", "v1", credentials=creds),
        build("drive", "v3", credentials=creds),
    )


def extract_text(shape: dict) -> str:
    if "text" not in shape:
        return ""
    return "".join(
        el["textRun"]["content"]
        for el in shape["text"].get("textElements", [])
        if "textRun" in el
    ).strip()


def _get_first_run_style(shape: dict) -> dict:
    """Return the text style of the first text run in the shape."""
    for te in shape.get("text", {}).get("textElements", []):
        if "textRun" in te:
            return te["textRun"].get("style", {})
    return {}


def map_slide_elements(slide: dict, sequence: list) -> dict:
    """Sort text elements by (y, x) position and map them to role names.
    Values are dicts with objectId and the original text style."""
    elements = []
    for el in slide.get("pageElements", []):
        if "shape" not in el or "text" not in el["shape"]:
            continue
        if not extract_text(el["shape"]):
            continue
        t = el.get("transform", {})
        elements.append({
            "objectId": el["objectId"],
            "style": _get_first_run_style(el["shape"]),
            "y": t.get("translateY", 0),
            "x": t.get("translateX", 0),
        })
    elements.sort(key=lambda e: (e["y"], e["x"]))

    role_map = {}
    for i, role in enumerate(sequence):
        if i < len(elements) and role is not None:
            role_map[role] = {"objectId": elements[i]["objectId"], "style": elements[i]["style"]}
    return role_map


def replace_text(el: dict, text: str) -> list:
    """Build deleteText + insertText + updateTextStyle (preserves original color/font)."""
    oid = el["objectId"]
    style = el.get("style", {})

    if not text:
        return [{"deleteText": {"objectId": oid, "textRange": {"type": "ALL"}}}]

    reqs = [
        {"deleteText": {"objectId": oid, "textRange": {"type": "ALL"}}},
        {"insertText": {"objectId": oid, "insertionIndex": 0, "text": text}},
    ]

    # Restore the original text style so color/weight survive the replacement
    style_fields = [k for k in ("foregroundColor", "bold", "italic", "fontSize", "fontFamily", "underline") if k in style]
    if style_fields:
        reqs.append({
            "updateTextStyle": {
                "objectId": oid,
                "style": {k: style[k] for k in style_fields},
                "textRange": {"type": "ALL"},
                "fields": ",".join(style_fields),
            }
        })
    return reqs


def split_tagline(tagline: str) -> tuple:
    if "\n" in tagline:
        parts = tagline.split("\n", 1)
        return parts[0].strip(), parts[1].strip()
    return tagline, ""


def build_slide1_requests(m: dict, cov: dict) -> list:
    reqs = []
    for role, val in [
        ("badge", cov.get("badge", "")),
        ("main_title", cov.get("main_title", "")),
        ("subtitle_label", cov.get("subtitle_label", "")),
        ("subtitle_desc", cov.get("subtitle_desc", "")),
        ("client_name", cov.get("client_name", "")),
    ]:
        if role in m:
            reqs += replace_text(m[role], val)
    return reqs


def build_slide2_requests(m: dict, s: dict, slide_num: int, total: int) -> list:
    reqs = []
    t1, t2 = split_tagline(s.get("tagline", ""))
    for role, val in [
        ("section_label", s.get("section_label", "")),
        ("tagline_1", t1), ("tagline_2", t2),
        ("sub_desc", s.get("sub_description", "")),
    ]:
        if role in m:
            reqs += replace_text(m[role], val)

    cards = s.get("cards", [])
    for i in range(6):
        card = cards[i] if i < len(cards) else {}
        for sub, val in [
            ("title", card.get("title", "")),
            ("badge", card.get("badge", "")),
            ("desc", card.get("description", "")),
            ("details", card.get("details", "")),
        ]:
            role = f"card.{i}.{sub}"
            if role in m:
                reqs += replace_text(m[role], val)

    if "footer" in m:
        reqs += replace_text(m["footer"], f"# {slide_num} of {total}")
    return reqs


def build_slide3_requests(m: dict, s: dict, slide_num: int, total: int) -> list:
    reqs = []
    t1, t2 = split_tagline(s.get("tagline", ""))
    for role, val in [
        ("section_label", s.get("section_label", "")),
        ("tagline_1", t1), ("tagline_2", t2),
        ("sub_desc", s.get("sub_description", "")),
    ]:
        if role in m:
            reqs += replace_text(m[role], val)

    items = s.get("items", [])
    for i in range(6):
        item = items[i] if i < len(items) else {}
        for sub, val in [
            ("icon", item.get("icon", "")),
            ("title", item.get("title", "")),
            ("desc", item.get("description", "")),
            ("source", item.get("source", "")),
        ]:
            role = f"item.{i}.{sub}"
            if role in m:
                reqs += replace_text(m[role], val)

    if "footer" in m:
        reqs += replace_text(m["footer"], f"# {slide_num} of {total}")
    return reqs


def build_slide4_requests(m: dict, s: dict, slide_num: int, total: int) -> list:
    reqs = []
    t1, t2 = split_tagline(s.get("tagline", ""))
    for role, val in [
        ("section_label", s.get("section_label", "")),
        ("tagline_1", t1), ("tagline_2", t2),
        ("sub_desc", s.get("sub_description", "")),
    ]:
        if role in m:
            reqs += replace_text(m[role], val)

    asks = s.get("asks", [])
    for i in range(4):
        ask = asks[i] if i < len(asks) else {}
        num = f"0{i+1}" if i + 1 < 10 else str(i + 1)
        for sub, val in [
            ("num", ask.get("num", num) if ask else ""),
            ("title", ask.get("title", "")),
            ("desc", ask.get("description", "")),
            ("unlocks", f"UNLOCKS  {ask['unlocks']}" if ask.get("unlocks") else ""),
        ]:
            role = f"ask.{i}.{sub}"
            if role in m:
                reqs += replace_text(m[role], val)
        if i in (0, 2):
            example_val = f"Example:  {ask['example']}" if ask.get("example") else ""
            role = f"ask.{i}.example"
            if role in m:
                reqs += replace_text(m[role], example_val)

    if "footer" in m:
        reqs += replace_text(m["footer"], f"# {slide_num} of {total}")
    return reqs


def build_slide5_requests(m: dict, s: dict, slide_num: int, total: int) -> list:
    reqs = []
    t1, t2 = split_tagline(s.get("tagline", ""))
    for role, val in [
        ("section_label", s.get("section_label", "")),
        ("tagline_1", t1), ("tagline_2", t2),
        ("sub_desc", s.get("sub_description", "")),
    ]:
        if role in m:
            reqs += replace_text(m[role], val)

    for i, week in enumerate(s.get("weeks", [{}, {}])[:2]):
        for sub, val in [
            ("label", week.get("label", f"W{i+1}")),
            ("phase", week.get("phase", "")),
            ("title", week.get("title", "")),
            ("desc", week.get("description", "")),
            ("bullets", week.get("bullets", "")),
        ]:
            role = f"week.{i}.{sub}"
            if role in m:
                reqs += replace_text(m[role], val)

    if "footer" in m:
        reqs += replace_text(m["footer"], f"# {slide_num} of {total}")
    return reqs


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="create_reshapex_brief",
            description=(
                "Creates a ReshapeX Internal Brief in Google Slides. "
                "Copies the visual template and replaces ALL text with user content. "
                "Only cover is required. Content slides (cards, items, asks, weeks) are optional — "
                "unused slides are deleted automatically and footers renumbered. "
                "Returns the Google Slides URL."
            ),
            inputSchema={
                "type": "object",
                "required": ["title", "cover"],
                "properties": {
                    "title": {"type": "string", "description": "Google Drive file name"},
                    "cover": {
                        "type": "object",
                        "required": ["badge", "main_title", "subtitle_label", "subtitle_desc", "client_name"],
                        "properties": {
                            "badge": {"type": "string", "description": "e.g. 'INTERNAL BRIEF · JUNE 2026'"},
                            "main_title": {"type": "string"},
                            "subtitle_label": {"type": "string", "description": "e.g. 'Overview'"},
                            "subtitle_desc": {"type": "string"},
                            "client_name": {"type": "string"},
                        },
                    },
                    "slide2": {
                        "type": "object",
                        "description": "Card grid slide (3x2, 6 cards max). Omit to skip.",
                        "required": ["section_label", "tagline", "sub_description", "cards"],
                        "properties": {
                            "section_label": {"type": "string"},
                            "tagline": {"type": "string", "description": "Use \\n to break into two lines"},
                            "sub_description": {"type": "string"},
                            "cards": {
                                "type": "array", "minItems": 1, "maxItems": 6,
                                "items": {
                                    "type": "object",
                                    "required": ["title", "badge", "description", "details"],
                                    "properties": {
                                        "title": {"type": "string"},
                                        "badge": {"type": "string", "description": "STRONG / PARTIAL / GAP / HTML ONLY / UI ONLY / FALLBACK / DONE / PENDING / RISK"},
                                        "description": {"type": "string"},
                                        "details": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                    "slide3": {
                        "type": "object",
                        "description": "Icon-item slide (3x2, 6 items max). Omit to skip.",
                        "required": ["section_label", "tagline", "sub_description", "items"],
                        "properties": {
                            "section_label": {"type": "string"},
                            "tagline": {"type": "string"},
                            "sub_description": {"type": "string"},
                            "items": {
                                "type": "array", "minItems": 1, "maxItems": 6,
                                "items": {
                                    "type": "object",
                                    "required": ["icon", "title", "description", "source"],
                                    "properties": {
                                        "icon": {"type": "string", "description": "Single symbol: Q, =, v, +, ?, @, >, o"},
                                        "title": {"type": "string"},
                                        "description": {"type": "string"},
                                        "source": {"type": "string", "description": "e.g. '-> /api/v2/search/'"},
                                    },
                                },
                            },
                        },
                    },
                    "slide4": {
                        "type": "object",
                        "description": "Numbered asks slide (2x2, 4 asks max). Omit to skip.",
                        "required": ["section_label", "tagline", "sub_description", "asks"],
                        "properties": {
                            "section_label": {"type": "string"},
                            "tagline": {"type": "string"},
                            "sub_description": {"type": "string"},
                            "asks": {
                                "type": "array", "minItems": 1, "maxItems": 4,
                                "items": {
                                    "type": "object",
                                    "required": ["title", "description", "unlocks"],
                                    "properties": {
                                        "title": {"type": "string"},
                                        "description": {"type": "string"},
                                        "example": {"type": "string"},
                                        "unlocks": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                    "slide5": {
                        "type": "object",
                        "description": "Two-column week plan slide. Omit to skip.",
                        "required": ["section_label", "tagline", "sub_description", "weeks"],
                        "properties": {
                            "section_label": {"type": "string"},
                            "tagline": {"type": "string"},
                            "sub_description": {"type": "string"},
                            "weeks": {
                                "type": "array", "minItems": 1, "maxItems": 2,
                                "items": {
                                    "type": "object",
                                    "required": ["label", "phase", "title", "description", "bullets"],
                                    "properties": {
                                        "label": {"type": "string", "description": "e.g. W1"},
                                        "phase": {"type": "string", "description": "e.g. WEEK 1 · BUILD"},
                                        "title": {"type": "string"},
                                        "description": {"type": "string"},
                                        "bullets": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                },
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "create_reshapex_brief":
        raise ValueError(f"Unknown tool: {name}")

    try:
        slides_svc, drive_svc = get_services()

        # 1. Copy template
        copy = drive_svc.files().copy(
            fileId=TEMPLATE_ID,
            body={"name": arguments["title"]},
            supportsAllDrives=True,
        ).execute()
        pres_id = copy["id"]
        url = f"https://docs.google.com/presentation/d/{pres_id}/edit"

        # 2. Get presentation structure
        pres = slides_svc.presentations().get(presentationId=pres_id).execute()
        slide_pages = pres["slides"]

        # 3. Determine which slides to keep (cover always kept)
        # template indices: 0=cover, 1=cards(slide2), 2=items(slide3), 3=asks(slide4), 4=weeks(slide5)
        content_keys = ["slide2", "slide3", "slide4", "slide5"]
        keep_indices = [0]
        for i, key in enumerate(content_keys):
            if key in arguments and arguments[key]:
                keep_indices.append(i + 1)

        total_slides = len(keep_indices)

        # 4. Map elements for all template slides
        maps = [
            map_slide_elements(slide_pages[i], SLIDE_SEQUENCES[i])
            for i in range(min(5, len(slide_pages)))
        ]

        # 5. Build replacement requests
        requests = []
        slide_num = 0
        for template_idx in keep_indices:
            slide_num += 1
            m = maps[template_idx]
            if template_idx == 0:
                requests += build_slide1_requests(m, arguments["cover"])
            elif template_idx == 1:
                requests += build_slide2_requests(m, arguments["slide2"], slide_num, total_slides)
            elif template_idx == 2:
                requests += build_slide3_requests(m, arguments["slide3"], slide_num, total_slides)
            elif template_idx == 3:
                requests += build_slide4_requests(m, arguments["slide4"], slide_num, total_slides)
            elif template_idx == 4:
                requests += build_slide5_requests(m, arguments["slide5"], slide_num, total_slides)

        # 6. Delete unused slides (reverse order to preserve page indices)
        skip_indices = [i for i in range(len(slide_pages)) if i not in keep_indices]
        delete_requests = [
            {"deleteObject": {"objectId": slide_pages[i]["objectId"]}}
            for i in reversed(skip_indices)
            if i < len(slide_pages)
        ]
        # Deletes must happen before text replacements since they change page count
        all_requests = delete_requests + requests

        if all_requests:
            slides_svc.presentations().batchUpdate(
                presentationId=pres_id,
                body={"requests": all_requests},
            ).execute()

        slide_word = "slide" if total_slides == 1 else "slides"
        return [types.TextContent(
            type="text",
            text=f"Presentation created: {total_slides} {slide_word}.\n\nURL: {url}",
        )]

    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {e}")]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="reshapex-mcp",
                server_version="0.3.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
