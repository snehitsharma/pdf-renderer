import re
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Flowable, Paragraph, Spacer, Table, TableStyle

# ==========================================================================
#  INLINE MARKUP & TEXT HELPERS — **bold**, *italic*, [text](url)
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
#  LOW-LEVEL DRAWING PRIMITIVES
# ==========================================================================


class Rule(Flowable):
    """Horizontal line divider with exact width, thickness, and color."""
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
#  LAYOUT HELPERS
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
    """One row: free-flowing left text + hard right-aligned date column."""
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


# ==========================================================================
#  SHARED BUILDING BLOCKS
# ==========================================================================


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


# ==========================================================================
#  SECTION COMPONENTS
# ==========================================================================


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
