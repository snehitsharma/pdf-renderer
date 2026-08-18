import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE)

CONFIG = {
    "page": {
        "size": "A4",             # "A4" or "LETTER"
        "margin_left": 45,        # 0.625"
        "margin_right": 45,
        "margin_top": 40,
        "margin_bottom": 36,
    },

    "font": {
        # family name -> (regular, bold, italic, bold-italic) TTF paths
        "family": "Carlito",
        # Bare filenames — resolved against search_dirs below, in order.
        "paths": {
            "regular": "Carlito-Regular.ttf",
            "bold": "Carlito-Bold.ttf",
            "italic": "Carlito-Italic.ttf",
            "boldItalic": "Carlito-BoldItalic.ttf",
        },
        "search_dirs": [
            os.path.join(_PROJECT_ROOT, "assets", "font"),
            os.path.join(_PROJECT_ROOT, "assets", "fonts"),
            os.path.join(_PROJECT_ROOT, "fonts"),
            os.path.join(_PROJECT_ROOT, "font"),
            os.path.join(_HERE, "fonts"),
            os.path.join(_HERE, "font"),
            os.path.join(os.getcwd(), "assets", "font"),
            os.path.join(os.getcwd(), "fonts"),
            os.path.join(os.getcwd(), "font"),
            "/usr/share/fonts/truetype/crosextra",
            "/usr/share/fonts/truetype",
            "C:/Windows/Fonts",
            "/Library/Fonts",
            os.path.expanduser("~/.fonts"),
        ],
    },

    "type": {
        # element        size  leading  tracking
        "name":          {"size": 19.0, "leading": 22.0, "tracking": 1.4},
        "headline":      {"size": 9.5,  "leading": 12.0, "tracking": 0.0},
        "contact":       {"size": 9.5,  "leading": 12.0, "tracking": 0.0},
        "section":       {"size": 11.5, "leading": 13.5, "tracking": 0.9},
        "entry":         {"size": 10.0, "leading": 12.4, "tracking": 0.0},
        "dates":         {"size": 10.0, "leading": 12.4, "tracking": 0.0},
        "stack":         {"size": 9.5,  "leading": 11.8, "tracking": 0.0},
        "bullet":        {"size": 10.0, "leading": 12.6, "tracking": 0.0},
        "skills":        {"size": 10.0, "leading": 12.8, "tracking": 0.0},
    },

    # ONE accent colour, used for the name, section headings, rules and links.
    "accent": "#1F4E79",

    "color": {
        "name":      "@accent",
        "headline":  "#333333",
        "contact":   "#333333",
        "section":   "@accent",
        "body":      "#000000",
        "entry":     "#000000",
        "dates":     "#333333",
        "stack":     "#444444",
        "link":      "@accent",
        "rule":      "@accent",
    },

    "spacing": {
        # --- header ---
        "name_after": 3.0,
        "headline_after": 2.5,
        "contact_after": 10.0,

        # --- section headings ---
        "section_before": 9.0,     # gap above a section heading
        "heading_to_rule": 2.0,    # heading baseline gap to its rule
        "rule_to_content": 4.5,    # rule to first entry
        "rule_thickness": 0.7,

        # --- entries ---
        "entry_to_bullets": 1.5,   # header line -> first bullet
        "between_bullets": 2.0,
        "between_entries": 6.5,    # last bullet of entry -> next entry header
        "between_edu_entries": 2.5,

        # --- projects ---
        "project_title_to_stack": 1.0,
        "stack_to_bullets": 2.0,
        "between_projects": 6.5,

        # --- skills ---
        "between_skill_rows": 1.5,
    },

    "bullets": {
        "char": "\u2022",
        "indent": 8.0,        # x of the bullet glyph, relative to left margin
        "text_indent": 19.0,  # x where text starts (hanging indent for wraps)
        "justify": False,     # True = justified body text, False = ragged right
    },

    "dates": {
        "min_col_width": 92.0,   # right-hand date column
        "gutter": 10.0,          # min gap between left text and date column
    },

    "autofit": {
        "enabled": True,
        "target_pages": 1,
        # each pass multiplies all spacing + leading by this, down to floor
        "step": 0.94,
        "floor": 0.72,
        # if spacing alone can't do it, shrink body sizes by this many points
        "font_shrink_steps": [0.0, 0.25, 0.5],
        # --fill: if content is short, grow spacing (never fonts) to balance
        "fill_enabled": False,
        "fill_ceiling": 1.9,
        "fill_step": 1.03,
    },
}
