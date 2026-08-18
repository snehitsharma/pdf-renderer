import io
import os
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
)

from services.components import Rule, TrackedLine


def get_story_builder(template_name="classic"):
    """Lazy loader for templates to avoid module-level circular imports."""
    if template_name == "classic":
        from services.templates import classic
        return classic.build_story
    raise ValueError(f"Unknown template '{template_name}'")


# ==========================================================================
#  FONT & COLOR SETUP
# ==========================================================================


def _find_font(path, filename, search_dirs):
    if os.path.exists(path):
        return path
    for d in search_dirs:
        cand = os.path.join(d, filename)
        if os.path.exists(cand):
            return cand
    return None


def resolve_accent(cfg):
    """Expand every '@accent' placeholder to the configured accent colour."""
    acc = cfg.get("accent", "#000000")
    for k, v in cfg["color"].items():
        if v == "@accent":
            cfg["color"][k] = acc
    return cfg


def register_fonts(cfg):
    fam = cfg["font"]["family"]
    paths = cfg["font"]["paths"]
    dirs = cfg["font"]["search_dirs"]

    resolved = {}
    for key, p in paths.items():
        found = _find_font(p, os.path.basename(p), dirs)
        if found is None and key == "boldItalic":
            found = resolved.get("bold") or resolved.get("regular")
        if found is None:
            print(
                f"  ! {fam} {key} not found ({p}) — falling back to Helvetica",
                file=sys.stderr,
            )
            return {
                "regular": "Helvetica",
                "bold": "Helvetica-Bold",
                "italic": "Helvetica-Oblique",
                "boldItalic": "Helvetica-BoldOblique",
            }
        resolved[key] = found

    names = {
        "regular": fam,
        "bold": fam + "-Bold",
        "italic": fam + "-Italic",
        "boldItalic": fam + "-BoldItalic",
    }
    for key, name in names.items():
        pdfmetrics.registerFont(TTFont(name, resolved[key]))
    pdfmetrics.registerFontFamily(
        fam,
        normal=names["regular"],
        bold=names["bold"],
        italic=names["italic"],
        boldItalic=names["boldItalic"],
    )
    return names


# ==========================================================================
#  STYLE BUILDER
# ==========================================================================


def build_styles(cfg, fonts, scale=1.0, font_delta=0.0):
    t = cfg["type"]
    c = cfg["color"]
    b = cfg["bullets"]

    def sz(key):
        return t[key]["size"] - (font_delta if key in ("bullet", "entry", "skills", "stack", "dates") else 0.0)

    def ld(key):
        return (t[key]["leading"] - (font_delta if key != "name" else 0.0)) * scale

    S = {}

    S["name"] = ParagraphStyle(
        "name", fontName=fonts["bold"], fontSize=t["name"]["size"],
        leading=t["name"]["leading"], alignment=TA_CENTER,
        textColor=colors.HexColor(c["name"]),
        spaceAfter=0,
    )
    S["name"].charSpace = t["name"]["tracking"]

    S["headline"] = ParagraphStyle(
        "headline", fontName=fonts["regular"], fontSize=t["headline"]["size"],
        leading=ld("headline"), alignment=TA_CENTER,
        textColor=colors.HexColor(c["headline"]),
    )

    S["contact"] = ParagraphStyle(
        "contact", fontName=fonts["regular"], fontSize=t["contact"]["size"],
        leading=ld("contact"), alignment=TA_CENTER,
        textColor=colors.HexColor(c["contact"]),
    )

    S["section"] = ParagraphStyle(
        "section", fontName=fonts["bold"], fontSize=t["section"]["size"],
        leading=ld("section"), alignment=TA_LEFT,
        textColor=colors.HexColor(c["section"]),
    )
    S["section"].charSpace = t["section"]["tracking"]

    S["entry"] = ParagraphStyle(
        "entry", fontName=fonts["regular"], fontSize=sz("entry"),
        leading=ld("entry"), alignment=TA_LEFT,
        textColor=colors.HexColor(c["entry"]),
    )

    S["dates"] = ParagraphStyle(
        "dates", fontName=fonts["regular"], fontSize=sz("dates"),
        leading=ld("dates"), alignment=2,  # TA_RIGHT
        textColor=colors.HexColor(c["dates"]),
    )

    S["stack"] = ParagraphStyle(
        "stack", fontName=fonts["italic"], fontSize=sz("stack"),
        leading=ld("stack"), alignment=TA_LEFT,
        textColor=colors.HexColor(c["stack"]),
    )

    S["bullet"] = ParagraphStyle(
        "bullet", fontName=fonts["regular"], fontSize=sz("bullet"),
        leading=ld("bullet"),
        alignment=TA_JUSTIFY if b["justify"] else TA_LEFT,
        textColor=colors.HexColor(c["body"]),
        leftIndent=b["text_indent"],
        bulletIndent=b["indent"],
        bulletFontName=fonts["regular"],
        bulletFontSize=sz("bullet"),
    )

    S["skills"] = ParagraphStyle(
        "skills", fontName=fonts["regular"], fontSize=sz("skills"),
        leading=ld("skills"), alignment=TA_LEFT,
        textColor=colors.HexColor(c["body"]),
    )

    return S


# ==========================================================================
#  DOCUMENT BUILD & RENDER ENGINE
# ==========================================================================


def render_once(data, cfg, fonts, out_stream, scale, font_delta, story_builder=None):
    if story_builder is None:
        template_name = cfg.get("template", "classic")
        story_builder = get_story_builder(template_name)

    pagesize = A4 if cfg["page"]["size"].upper() == "A4" else LETTER
    pw, ph = pagesize
    m = cfg["page"]
    content_width = pw - m["margin_left"] - m["margin_right"]
    content_height = ph - m["margin_top"] - m["margin_bottom"]

    doc = BaseDocTemplate(
        out_stream,
        pagesize=pagesize,
        leftMargin=m["margin_left"],
        rightMargin=m["margin_right"],
        topMargin=m["margin_top"],
        bottomMargin=m["margin_bottom"],
        title=data["header"]["name"],
        author=data["header"]["name"],
        creator=data["header"]["name"],
        producer=data["header"]["name"],
    )
    frame = Frame(
        m["margin_left"], m["margin_bottom"],
        content_width, content_height,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        id="body",
    )
    doc.addPageTemplates([PageTemplate(id="resume", frames=[frame])])

    story = story_builder(data, cfg, fonts, scale, font_delta, content_width)
    doc.build(story)
    return doc.page  # number of pages produced


def render_to_bytes(data, cfg):
    resolve_accent(cfg)
    fonts = register_fonts(cfg)
    template_name = cfg.get("template", "classic")
    story_builder = get_story_builder(template_name)
    af = cfg["autofit"]

    attempts = []
    if af["enabled"]:
        for fd in af["font_shrink_steps"]:
            s = 1.0
            while s >= af["floor"] - 1e-9:
                attempts.append((s, fd))
                s *= af["step"]
    else:
        attempts = [(1.0, 0.0)]

    chosen = None
    for scale, fd in attempts:
        buf = io.BytesIO()
        pages = render_once(data, cfg, fonts, buf, scale, fd, story_builder)
        if pages <= af["target_pages"] or not af["enabled"]:
            chosen = (scale, fd, pages, buf.getvalue())
            break

    if chosen is None:
        buf = io.BytesIO()
        scale, fd = attempts[-1]
        pages = render_once(data, cfg, fonts, buf, scale, fd, story_builder)
        chosen = (scale, fd, pages, buf.getvalue())
        print("  ! could not fit target page count at minimum density", file=sys.stderr)

    scale, fd, pages, blob = chosen

    # optional: grow spacing until one more step would overflow
    if af.get("fill_enabled") and fd == 0.0 and pages <= af["target_pages"]:
        s_try = scale
        while s_try * af["fill_step"] <= af["fill_ceiling"]:
            nxt = s_try * af["fill_step"]
            buf = io.BytesIO()
            n = render_once(data, cfg, fonts, buf, nxt, 0.0, story_builder)
            if n > af["target_pages"]:
                break
            s_try, blob, pages = nxt, buf.getvalue(), n
        scale = s_try

    return blob, pages, scale, fd


def render(data, cfg, out_path):
    blob, pages, scale, fd = render_to_bytes(data, cfg)
    with open(out_path, "wb") as f:
        f.write(blob)
    print(f"  wrote {out_path}")
    print(f"  pages={pages}  spacing_scale={scale:.3f}  font_delta=-{fd}pt")
    return out_path