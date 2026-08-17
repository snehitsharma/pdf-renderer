# resume-renderer

Deterministic resume to PDF compiler. You supply structured content; it owns every measurement (margins, leading, indents, date alignment, section spacing).

Same input always produces the same bytes output. Fonts are bundled (Caladea, SIL OFL 1.1), rendering identically across operating systems without manual font installation.

---

## Quickstart: Windows

### 1. Install Python

Download from [python.org](https://www.python.org/downloads/) and ensure **"Add python.exe to PATH"** is selected.

Verify in PowerShell:

```powershell
python --version
```

### 2. Project Structure

```
resume-renderer/
├── render_resume.py
├── resume.json
├── requirements.txt
└── font/
    ├── Caladea-Regular.ttf
    ├── Caladea-Bold.ttf
    └── Caladea-Italic.ttf
```

### 3. Install Dependencies

Open PowerShell in the project directory and run:

```powershell
pip install -r requirements.txt
```

### 4. Run Renderer

```powershell
python render_resume.py resume.json -o Snehit-Sharma-Resume.pdf
```

The compiled PDF will be generated in the current directory.

---

## Options

```
--fill              Expand spacing to balance a short resume on the page
--pages 2           Allow two pages target
--no-fit            Fixed density, no auto-shrink
--accent "#1F4E79"  Custom accent color (name, headings, rules, links)
--size LETTER       US Letter page size instead of A4
```

## Customization

- **Content**: Edit `resume.json` (or `.yaml` / `.txt`).
- **Design & Layout**: Edit the `CONFIG` dictionary at the top of `render_resume.py` to customize margins, font sizes, leading, tracking, and accent colors.

---

## Remaining Tasks / Roadmap

- [ ] Add LLM to automate resume builder
- [ ] Add a frontend
- [ ] Add more templates
- [ ] Add a cloud save for the resumes

---

## License

Bundled Caladea fonts are under SIL Open Font License 1.1.
