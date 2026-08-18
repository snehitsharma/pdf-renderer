from reportlab.platypus import Spacer
from services.components import (
    date_col_width,
    education_entry,
    experience_entry,
    header_block,
    project_entry,
    section_heading,
    skills_block,
)
from services.renderer import build_styles


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
