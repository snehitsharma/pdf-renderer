# Resume PDF Renderer

A deterministic resume-to-PDF compilation engine with both a **CLI** and a **FastAPI REST Web Service**. 

Supply structured resume content (JSON, YAML, or plain text); the engine handles every pixel, margin, line-leading, indent, right-aligned date column, section spacing, and single/multi-page auto-fitting dynamically.

---

## Features

- **Deterministic PDF Generation**: Identical input always yields identical PDF bytes.
- **Dual Interface**:
  - **CLI (`cli.py`)**: Generate PDFs directly from terminal commands.
  - **FastAPI Web API (`app.py`)**: High-performance REST service for web app integrations.
- **Multiple Input Formats**: Accepts `.json`, `.yaml`, or `.txt` formatted resume content.
- **Smart Auto-Fit Scaling**: Automatically calculates font sizes and vertical spacing to balance your resume cleanly on 1 or 2 pages.
- **Bundled Open Fonts**: Bundles SIL-licensed Caladea fonts for cross-platform visual consistency across Windows, macOS, and Linux.

---

## Quickstart

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Running via CLI

Generate a PDF from a resume content file:

```bash
python resume-pdf/cli.py resume.json -o resume.pdf
```

#### CLI Options:
```bash
python resume-pdf/cli.py resume.json \
  -o output.pdf \
  --accent "#1F4E79" \
  --size LETTER \
  --pages 1 \
  --fill
```

- `--accent "#HEX"`: Custom accent color for headings, dividers, and links.
- `--size A4|LETTER`: Target page size (default: `A4`).
- `--pages 1`: Target page count for auto-fit scaling.
- `--fill`: Expand spacing to balance short content evenly across the page.
- `--no-fit`: Disable auto-fitting algorithms.

---

## Running the FastAPI REST Web Server

Start the interactive FastAPI web server:

```bash
python resume-pdf/app.py
```
*(Or run `uvicorn resume-pdf.app:app --reload`)*

The server will launch at **`http://localhost:8000`**.

### Interactive Swagger UI API Docs

Open **`http://localhost:8000/docs`** in your browser to test endpoints interactively.

### API Endpoints

#### 1. `POST /render` (JSON Body)
Pass raw JSON resume payload in the request body to receive the compiled PDF stream.

```bash
curl -X POST "http://localhost:8000/render?accent=%231F4E79&pages=1" \
  -H "Content-Type: application/json" \
  -d '{
    "header": { "name": "Jane Doe", "contact": [{"text": "jane@example.com"}] },
    "experience": [...]
  }' \
  --output my_resume.pdf
```

#### 2. `POST /render/file` (File Upload)
Upload a `.json`, `.yaml`, or `.txt` file over HTTP.

```bash
curl -X POST "http://localhost:8000/render/file?accent=%231F4E79" \
  -F "file=@resume.json" \
  --output my_resume.pdf
```

---

## Project Architecture

```
pdf-render/
├── requirements.txt         # Dependencies (ReportLab, PyYAML, FastAPI, Uvicorn)
├── resume-pdf/
│   ├── app.py               # FastAPI Web API endpoints
│   ├── cli.py               # CLI entry point
│   ├── config.py            # Design tokens, typography & layout parameters
│   ├── parser.py            # Parser for JSON, YAML, and TXT input formats
│   ├── renderer.py          # ReportLab PDF compilation engine (in-memory & file)
│   └── font/                # Bundled TTF fonts (Caladea)
```

---

## License

Bundled Caladea fonts are licensed under the SIL Open Font License 1.1.
