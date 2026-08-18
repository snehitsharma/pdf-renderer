import io
import json
import os
import re
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

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
#  INLINE MARKUP  —  **bold**, *italic*, [text](url)
# ==========================================================================

_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.S)
_ITAL_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", re.S)


def esc(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def inline(text, link_color="#1155CC"):
    """Escape, then convert lightweight markup into ReportLab inline tags."""
    out = esc(text)
    out = _BOLD_RE.sub(r"<b>\1</b>", out)
    out = _ITAL_RE.sub(r"<i>\1</i>", out)
    out = _LINK_RE.sub(
        lambda m: f'<link href="{m.group(2)}" color="{link_color}"><u>{m.group(1)}</u></link>',
        out,
    )
    return out


def link(text, url, color):
    if not url:
        return esc(text)
    return f'<link href="{esc(url)}" color="{color}"><u>{esc(text)}</u></link>'




# ==========================================================================
#  RULE FLOWABLE (section divider) — exact width, exact thickness
# ==========================================================================


class Rule(Flowable):
    def __init__(self, width, thickness, color, space_before=0, space_after=0):
        Flowable.__init__(self)
        self._w = width
        self._t = thickness
        self._c = color
        self._sb = space_before
        self._sa = space_after
        self.height = thickness + space_before + space_after

    def wrap(self, availWidth, availHeight):
        self._w = availWidth
        return availWidth, self.height

    def draw(self):
        self.canv.setStrokeColor(self._c)
        self.canv.setLineWidth(self._t)
        y = self._sa + self._t / 2.0
        self.canv.line(0, y, self._w, y)




class TrackedLine(Flowable):
    """Single-line text with real letter-spacing (ReportLab Paragraph has none).

    Used for the name and section headings, which are always one line.
    """

    def __init__(self, text, font, size, leading, tracking, color, align="left"):
        Flowable.__init__(self)
        self.text = text
        self.font = font
        self.size = size
        self.leading = leading
        self.tracking = tracking
        self.color = color
        self.align = align
        self.height = leading

    def _width(self):
        w = pdfmetrics.stringWidth(self.text, self.font, self.size)
        if len(self.text) > 1:
            w += self.tracking * (len(self.text) - 1)
        return w

    def wrap(self, availWidth, availHeight):
        self._avail = availWidth
        return availWidth, self.leading

    def draw(self):
        c = self.canv
        c.setFont(self.font, self.size)
        c.setFillColor(self.color)
        w = self._width()
        if self.align == "center":
            x = (self._avail - w) / 2.0
        elif self.align == "right":
            x = self._avail - w
        else:
            x = 0
        y = self.leading - self.size * 0.88
        to = c.beginText(x, y)
        to.setCharSpace(self.tracking)
        to.setFont(self.font, self.size)
        to.setFillColor(self.color)
        to.textOut(self.text)
        c.drawText(to)


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
    # tracking via charSpace is set at draw-time on the Paragraph
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
#  COMPONENTS
# ==========================================================================


def date_col_width(data, style, cfg):
    """Right column is exactly as wide as the widest date string + gutter."""
    widest = 0.0
    for group in ("education", "experience"):
        for e in data.get(group, []):
            d = e.get("dates", "")
            if d:
                widest = max(
                    widest, pdfmetrics.stringWidth(d, style.fontName, style.fontSize)
                )
    return max(cfg["dates"]["min_col_width"], widest + 4.0)


def two_col_row(left_html, right_html, styles, content_width, date_w, cfg):
    """One row: free-flowing left text + hard right-aligned date column.

    This is what kills the ragged-date problem — the date is not padded with
    spaces, it lives in its own right-aligned table cell.
    """
    left_w = content_width - date_w - cfg["dates"]["gutter"]
    tbl = Table(
        [[Paragraph(left_html, styles["entry"]), Paragraph(right_html, styles["dates"])]],
        colWidths=[left_w + cfg["dates"]["gutter"], date_w],
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]),
    )
    return tbl


def section_heading(title, styles, cfg, sp):
    st = styles["section"]
    return [
        Spacer(1, sp["section_before"]),
        TrackedLine(title.upper(), st.fontName, st.fontSize, st.leading,
                    cfg["type"]["section"]["tracking"], st.textColor, "left"),
        Spacer(1, sp["heading_to_rule"]),
        Rule(0, cfg["spacing"]["rule_thickness"], colors.HexColor(cfg["color"]["rule"])),
        Spacer(1, sp["rule_to_content"]),
    ]


def bullet_list(items, styles, cfg, sp):
    out = []
    for i, txt in enumerate(items):
        if i:
            out.append(Spacer(1, sp["between_bullets"]))
        out.append(
            Paragraph(
                inline(txt, cfg["color"]["link"]),
                styles["bullet"],
                bulletText=cfg["bullets"]["char"],
            )
        )
    return out


def education_entry(e, styles, cfg, content_width, date_w):
    parts = [f'<b>{esc(e["institution"])}</b>']
    if e.get("detail"):
        parts.append(esc(e["detail"]))
    line = " - ".join(parts)
    if e.get("extra"):
        line += f' | {esc(e["extra"])}'
    return two_col_row(line, esc(e.get("dates", "")), styles, content_width, date_w, cfg)


def experience_entry(e, styles, cfg, sp, content_width, date_w):
    bits = [f'<b>{esc(e["title"])}</b>']
    if e.get("company"):
        bits.append(f'<b>{esc(e["company"])}</b>')
    if e.get("location"):
        bits.append(esc(e["location"]))
    header = " | ".join(bits)

    flow = [two_col_row(header, esc(e.get("dates", "")), styles, content_width, date_w, cfg)]
    if e.get("bullets"):
        flow.append(Spacer(1, sp["entry_to_bullets"]))
        flow += bullet_list(e["bullets"], styles, cfg, sp)
    return flow


def project_entry(p, styles, cfg, sp):
    title = f'<b>{esc(p["name"])}</b>'
    if p.get("note"):
        title += f' ({esc(p["note"])})'
    if p.get("link"):
        title += " | " + link(p["link"]["text"], p["link"].get("url"), cfg["color"]["link"])

    flow = [Paragraph(title, styles["entry"])]
    if p.get("stack"):
        flow.append(Spacer(1, sp["project_title_to_stack"]))
        stack_txt = esc(p["stack"]).replace(" \u00b7 ", "&nbsp;&nbsp;\u00b7&nbsp;&nbsp;")
        flow.append(Paragraph(stack_txt, styles["stack"]))
    if p.get("bullets"):
        flow.append(Spacer(1, sp["stack_to_bullets"]))
        flow += bullet_list(p["bullets"], styles, cfg, sp)
    return flow


def skills_block(rows, styles, cfg, sp):
    flow = []
    for i, r in enumerate(rows):
        if i:
            flow.append(Spacer(1, sp["between_skill_rows"]))
        flow.append(
            Paragraph(f'<b>{esc(r["label"])}:</b> {esc(r["items"])}', styles["skills"])
        )
    return flow


def header_block(h, styles, cfg, sp):
    ns = styles["name"]
    flow = [TrackedLine(h["name"], ns.fontName, ns.fontSize, ns.leading,
                        cfg["type"]["name"]["tracking"], ns.textColor, "center")]
    if h.get("headline"):
        flow.append(Spacer(1, sp["name_after"]))
        flow.append(Paragraph(esc(h["headline"]), styles["headline"]))
    if h.get("contact"):
        pieces = [
            link(c["text"], c.get("url"), cfg["color"]["link"]) for c in h["contact"]
        ]
        flow.append(Spacer(1, sp["headline_after"]))
        flow.append(Paragraph("&nbsp;|&nbsp; ".join(pieces), styles["contact"]))
    flow.append(Spacer(1, sp["contact_after"]))
    return flow


# ==========================================================================
#  DOCUMENT BUILD
# ==========================================================================


def build_story(data, cfg, fonts, scale, font_delta, content_width):
    styles = build_styles(cfg, fonts, scale, font_delta)
    sp = {k: v * scale for k, v in cfg["spacing"].items()}
    date_w = date_col_width(data, styles["dates"], cfg)

    story = []
    story += header_block(data["header"], styles, cfg, sp)

    if data.get("education"):
        story += section_heading("Education", styles, cfg, sp)
        for i, e in enumerate(data["education"]):
            if i:
                story.append(Spacer(1, sp["between_edu_entries"]))
            story.append(education_entry(e, styles, cfg, content_width, date_w))

    if data.get("experience"):
        story += section_heading("Work Experience", styles, cfg, sp)
        for i, e in enumerate(data["experience"]):
            if i:
                story.append(Spacer(1, sp["between_entries"]))
            story += experience_entry(e, styles, cfg, sp, content_width, date_w)

    if data.get("projects"):
        story += section_heading("Projects", styles, cfg, sp)
        for i, p in enumerate(data["projects"]):
            if i:
                story.append(Spacer(1, sp["between_projects"]))
            story += project_entry(p, styles, cfg, sp)

    if data.get("skills"):
        story += section_heading("Technical Skills", styles, cfg, sp)
        story += skills_block(data["skills"], styles, cfg, sp)

    return story


def render_once(data, cfg, fonts, out_stream, scale, font_delta):
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

    story = build_story(data, cfg, fonts, scale, font_delta, content_width)
    doc.build(story)
    return doc.page  # number of pages produced


def render_to_bytes(data, cfg):
    resolve_accent(cfg)
    fonts = register_fonts(cfg)
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
        pages = render_once(data, cfg, fonts, buf, scale, fd)
        if pages <= af["target_pages"] or not af["enabled"]:
            chosen = (scale, fd, pages, buf.getvalue())
            break

    if chosen is None:
        buf = io.BytesIO()
        scale, fd = attempts[-1]
        pages = render_once(data, cfg, fonts, buf, scale, fd)
        chosen = (scale, fd, pages, buf.getvalue())
        print("  ! could not fit target page count at minimum density", file=sys.stderr)

    scale, fd, pages, blob = chosen

    # optional: grow spacing until one more step would overflow
    if af.get("fill_enabled") and fd == 0.0 and pages <= af["target_pages"]:
        s_try = scale
        while s_try * af["fill_step"] <= af["fill_ceiling"]:
            nxt = s_try * af["fill_step"]
            buf = io.BytesIO()
            n = render_once(data, cfg, fonts, buf, nxt, 0.0)
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