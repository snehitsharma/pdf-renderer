import copy
import json
import os
import sys
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

# Ensure package directory is on sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(os.path.join(os.path.dirname(_HERE), ".env"))
except ImportError:
    pass

from core.auth import create_access_token, get_current_user, verify_credentials
from core.config import CONFIG
from models.resume import ResumeData
from services.parser import parse_and_validate
from services.renderer import render_to_bytes
from services.storage import save_pdf_to_disk

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


@app.post("/login", tags=["Auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 token login endpoint, directly integrated with Swagger UI's Authorize button.
    Default credentials: username='admin', password='admin'
    """
    if not verify_credentials(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "service": "Resume PDF Renderer API",
        "version": "1.0.0",
        "endpoints": {
            "login": "POST /login",
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
    #remove this and it breaks, no other body to support it, text file would  stay empty
    openapi_extra={
        "requestBody": {
            "content": {
                "text/plain": {
                    "schema": {
                        "type": "string",
                        "description": "Paste any unquoted raw text, JSON, or YAML resume content here",
                        "example": "your text here"
                    }
                },
                "application/json": {
                    "schema": {
                        "type": "string",
                        "description": "Paste raw text, JSON, or YAML here",
                        "example": "your file here"
                    }
                }
            },
            "required": True,
        }
    }
)
async def render_json(
    request: Request,
    company: Optional[str] = Query(None, description="Company name (defaults to 'General')"),
    role: Optional[str] = Query(None, description="Role name (defaults to 'Resume')"),
    output_dir: Optional[str] = Query(None, description="Base folder (defaults to d:/autoCV)"),
    accent: Optional[str] = Query(None, description="Custom accent hex color, e.g. #1F4E79"),
    size: Optional[str] = Query("A4", description="Page size: A4 or LETTER"),
    pages: int = Query(1, description="Target page count"),
    fill: bool = Query(False, description="Expand spacing for short content"),
    no_fit: bool = Query(False, description="Disable autofit page scaling"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Compile resume content (JSON, YAML, or freeform text) directly into a PDF binary stream."""
    raw_text = (await request.body()).decode("utf-8")
    resume_data = parse_and_validate(raw_text)
    
    cfg = _prepare_config(
        accent=accent,
        size=size,
        pages=pages,
        fill=fill,
        no_fit=no_fit,
    )

    pdf_bytes, page_count, scale, font_delta = render_to_bytes(
        resume_data.model_dump(),
        cfg,
    )

    applicant_name = resume_data.header.name if (resume_data.header and resume_data.header.name) else None
    file_path, filename = save_pdf_to_disk(
        pdf_bytes,
        company=company,
        role=role,
        applicant_name=applicant_name,
        output_dir=output_dir,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "X-Saved-Path": file_path,
            "X-Page-Count": str(page_count),
            "X-Spacing-Scale": f"{scale:.3f}",
            "X-Font-Delta": f"{font_delta:.2f}",
        },
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
    company: Optional[str] = Query(None, description="Company name (defaults to 'General')"),
    role: Optional[str] = Query(None, description="Role name (defaults to 'Resume')"),
    output_dir: Optional[str] = Query(None, description="Base folder (defaults to d:/autoCV)"),
    accent: Optional[str] = Query(None, description="Custom accent hex color, e.g. #1F4E79"),
    size: Optional[str] = Query("A4", description="Page size: A4 or LETTER"),
    pages: int = Query(1, description="Target page count"),
    fill: bool = Query(False, description="Expand spacing for short content"),
    no_fit: bool = Query(False, description="Disable autofit page scaling"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Upload a .json, .yaml, or .txt file over HTTP and compile it into a PDF."""
    try:
        content_bytes = await file.read()
        raw_text = content_bytes.decode("utf-8")

        resume_data = parse_and_validate(raw_text, file.filename or "")
        data_dict = resume_data.model_dump()

        cfg = _prepare_config(accent=accent, size=size, pages=pages, fill=fill, no_fit=no_fit)
        pdf_bytes, page_count, scale, font_delta = render_to_bytes(data_dict, cfg)

        applicant_name = resume_data.header.name if (resume_data.header and resume_data.header.name) else None
        file_path, filename = save_pdf_to_disk(
            pdf_bytes,
            company=company,
            role=role,
            applicant_name=applicant_name,
            output_dir=output_dir,
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Saved-Path": file_path,
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
