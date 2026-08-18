import copy
import os
import sys
from typing import Any, Dict, Optional

from fastapi import FastAPI, File, HTTPException, Query, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure package directory is on sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from core.config import CONFIG
from models.resume import ResumeData
from services.parser import parse_text
from services.renderer import render_to_bytes

app = FastAPI(
    title="Resume PDF Renderer API",
    description="Deterministic Resume to PDF Compilation API",
    version="1.0.0",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _prepare_config(
    accent: Optional[str] = None,
    size: Optional[str] = None,
    pages: int = 1,
    fill: bool = False,
    no_fit: bool = False,
) -> Dict[str, Any]:
    cfg = copy.deepcopy(CONFIG)
    if no_fit:
        cfg["autofit"]["enabled"] = False
    cfg["autofit"]["target_pages"] = pages
    if size:
        cfg["page"]["size"] = size.upper()
    if accent:
        cfg["accent"] = accent
    if fill:
        cfg["autofit"]["fill_enabled"] = True
    return cfg


@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "service": "Resume PDF Renderer API",
        "version": "1.0.0",
        "endpoints": {
            "render_json": "POST /render",
            "render_file": "POST /render/file",
            "docs": "/docs",
        },
    }


@app.post(
    "/render",
    tags=["Render"],
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Returns the generated PDF binary stream.",
        }
    },
)
def render_json(
    resume_data: ResumeData,
    accent: Optional[str] = Query(None, description="Custom accent hex color, e.g. #1F4E79"),
    size: Optional[str] = Query("A4", description="Page size: A4 or LETTER"),
    pages: int = Query(1, description="Target page count"),
    fill: bool = Query(False, description="Expand spacing for short content"),
    no_fit: bool = Query(False, description="Disable autofit page scaling"),
):
    """Compile JSON resume data directly into a PDF binary stream."""
    try:
        data_dict = resume_data.model_dump()
        cfg = _prepare_config(accent=accent, size=size, pages=pages, fill=fill, no_fit=no_fit)
        pdf_bytes, page_count, scale, font_delta = render_to_bytes(data_dict, cfg)

        filename = f"{data_dict.get('header', {}).get('name', 'Resume').replace(' ', '_')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Page-Count": str(page_count),
                "X-Spacing-Scale": f"{scale:.3f}",
                "X-Font-Delta": f"{font_delta:.2f}",
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to render PDF: {str(e)}",
        )


@app.post(
    "/render/file",
    tags=["Render"],
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Returns the generated PDF binary stream.",
        }
    },
)
async def render_file(
    file: UploadFile = File(..., description="Upload .json, .yaml, or .txt resume content file"),
    accent: Optional[str] = Query(None, description="Custom accent hex color, e.g. #1F4E79"),
    size: Optional[str] = Query("A4", description="Page size: A4 or LETTER"),
    pages: int = Query(1, description="Target page count"),
    fill: bool = Query(False, description="Expand spacing for short content"),
    no_fit: bool = Query(False, description="Disable autofit page scaling"),
):
    """Upload a .json, .yaml, or .txt file over HTTP and compile it into a PDF."""
    try:
        content_bytes = await file.read()
        raw_text = content_bytes.decode("utf-8")
        filename_lower = file.filename.lower() if file.filename else ""

        if filename_lower.endswith(".json"):
            import json
            data = json.loads(raw_text)
        elif filename_lower.endswith((".yaml", ".yml")):
            import yaml
            data = yaml.safe_load(raw_text)
        else:
            data = parse_text(raw_text)

        cfg = _prepare_config(accent=accent, size=size, pages=pages, fill=fill, no_fit=no_fit)
        pdf_bytes, page_count, scale, font_delta = render_to_bytes(data, cfg)

        output_name = f"{data.get('header', {}).get('name', 'Resume').replace(' ', '_')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{output_name}"',
                "X-Page-Count": str(page_count),
                "X-Spacing-Scale": f"{scale:.3f}",
                "X-Font-Delta": f"{font_delta:.2f}",
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process file: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
