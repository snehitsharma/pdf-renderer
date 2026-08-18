import json
import re

_URL_IN_ANGLE = re.compile(r"^(.*?)\s*<([^>]+)>\s*$")

_SECTION_ALIASES = {
    "education": "education",
    "work experience": "experience",
    "experience": "experience",
    "projects": "projects",
    "project": "projects",
    "technical skills": "skills",
    "skills": "skills",
}


def _split_link(token):
    """'GitHub <https://x>' -> ('GitHub', 'https://x')"""
    m = _URL_IN_ANGLE.match(token.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return token.strip(), None


def parse_text(raw):
    data = {"header": {"contact": []}, "education": [], "experience": [],
            "projects": [], "skills": []}
    section = None
    entry = None

    for lineno, line in enumerate(raw.splitlines(), 1):
        line = line.rstrip()
        if not line.strip() or line.lstrip().startswith("//"):
            continue
        stripped = line.strip()

        # ---- section marker ----
        if stripped.startswith("#"):
            key = stripped.lstrip("#").strip().lower()
            if key not in _SECTION_ALIASES:
                raise ValueError(f"line {lineno}: unknown section '{key}'")
            section = _SECTION_ALIASES[key]
            entry = None
            continue

        # ---- header fields ----
        upper = stripped.split(":", 1)[0].strip().upper()
        if section is None and upper in ("NAME", "HEADLINE", "CONTACT"):
            value = stripped.split(":", 1)[1].strip()
            if upper == "NAME":
                data["header"]["name"] = value
            elif upper == "HEADLINE":
                data["header"]["headline"] = value
            else:
                for tok in value.split("|"):
                    text, url = _split_link(tok)
                    if text:
                        item = {"text": text}
                        if url:
                            item["url"] = url
                        data["header"]["contact"].append(item)
            continue

        if section is None:
            raise ValueError(f"line {lineno}: content before any '# SECTION' marker")

        # ---- skills rows ----
        if section == "skills":
            if ":" not in stripped:
                raise ValueError(f"line {lineno}: skills row needs 'Label: items'")
            label, items = stripped.split(":", 1)
            data["skills"].append({"label": label.strip(), "items": items.strip()})
            continue

        # ---- entry header ----
        if stripped.startswith("@"):
            body = stripped[1:].strip()
            dates = ""
            if "::" in body:
                body, dates = [x.strip() for x in body.split("::", 1)]
            fields = [f.strip() for f in body.split("|")]

            if section == "education":
                entry = {"institution": fields[0]}
                if len(fields) > 1 and fields[1]:
                    entry["detail"] = fields[1]
                if len(fields) > 2 and fields[2]:
                    entry["extra"] = fields[2]
                if dates:
                    entry["dates"] = dates
                data["education"].append(entry)

            elif section == "experience":
                entry = {"title": fields[0], "bullets": []}
                if len(fields) > 1 and fields[1]:
                    entry["company"] = fields[1]
                if len(fields) > 2 and fields[2]:
                    entry["location"] = fields[2]
                if dates:
                    entry["dates"] = dates
                data["experience"].append(entry)

            else:  # projects
                name = fields[0]
                note = None
                m = re.match(r"^(.*?)\s*\((.+)\)\s*$", name)
                if m:
                    name, note = m.group(1).strip(), m.group(2).strip()
                entry = {"name": name, "bullets": []}
                if note:
                    entry["note"] = note
                if len(fields) > 1 and fields[1]:
                    text, url = _split_link(fields[1])
                    entry["link"] = {"text": text, "url": url}
                data["projects"].append(entry)
            continue

        # ---- tech stack line ----
        if stripped.startswith("~"):
            if entry is None:
                raise ValueError(f"line {lineno}: '~' stack line before any '@' entry")
            entry["stack"] = stripped[1:].strip()
            continue

        # ---- bullet ----
        if stripped.startswith(("-", "*", "\u2022")):
            if entry is None:
                raise ValueError(f"line {lineno}: bullet before any '@' entry")
            entry.setdefault("bullets", []).append(stripped[1:].strip())
            continue

        raise ValueError(f"line {lineno}: unrecognised line -> {stripped[:50]!r}")

    for k in ("education", "experience", "projects", "skills"):
        if not data[k]:
            data.pop(k)
    return data


def load_content(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    low = path.lower()
    if low.endswith(".json"):
        return json.loads(raw)
    if low.endswith((".yaml", ".yml")):
        import yaml
        return yaml.safe_load(raw)
    return parse_text(raw)
