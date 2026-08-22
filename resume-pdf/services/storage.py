import os
import re
from datetime import datetime
from typing import Optional, Tuple

DEFAULT_OUTPUT_DIR = os.environ.get("AUTOCV_OUTPUT_DIR", "d:/autoCV")


def sanitize_name(name: str) -> str:
    """Replaces spaces with underscores and removes invalid filesystem characters."""
    if not name:
        return ""
    cleaned = re.sub(r'[\\/:*?"<>|]', "", name)
    cleaned = cleaned.replace(" ", "_")
    return cleaned.strip("_")


def save_pdf_to_disk(
    pdf_bytes: bytes,
    company: Optional[str] = None,
    role: Optional[str] = None,
    applicant_name: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Saves PDF bytes to disk under structure:
    <output_dir>/[<company>/]<role>/<timestamp>/<applicant_name>_Resume.pdf

    Example:
    d:/autoCV/Tesla/AI_Engineer/2026-08-21_145627/Resume.pdf
    """
    base_dir = output_dir if output_dir and output_dir.strip() else DEFAULT_OUTPUT_DIR
    clean_company = sanitize_name(company or "")
    clean_role = sanitize_name(role or "") or "General_Role"
    clean_applicant = sanitize_name(applicant_name or "")

    # Timestamp folder
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    # Build folder structure: base_dir / [company /] role / timestamp
    if clean_company:
        folder_path = os.path.join(base_dir, clean_company, clean_role, timestamp)
    else:
        folder_path = os.path.join(base_dir, clean_role, timestamp)

    os.makedirs(folder_path, exist_ok=True)

    # Resume filename inside timestamp folder
    if clean_applicant:
        filename = f"{clean_applicant}_RESUME.pdf"
    else:
        filename = "RESUME.pdf"

    file_path = os.path.join(folder_path, filename)

    with open(file_path, "wb") as f:
        f.write(pdf_bytes)

    return file_path, filename
