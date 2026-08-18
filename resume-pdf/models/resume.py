# models/resume.py
from pydantic import BaseModel
from typing import List, Optional

class ContactItem(BaseModel):
    text: str
    url: Optional[str] = None

class Header(BaseModel):
    name: str
    headline: Optional[str] = None
    contact: List[ContactItem] = []

class EducationEntry(BaseModel):
    institution: str
    detail: Optional[str] = None
    extra: Optional[str] = None
    dates: Optional[str] = None

class ExperienceEntry(BaseModel):
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    dates: Optional[str] = None
    bullets: List[str] = []

class ProjectLink(BaseModel):
    text: str
    url: Optional[str] = None

class ProjectEntry(BaseModel):
    name: str
    note: Optional[str] = None
    link: Optional[ProjectLink] = None
    stack: Optional[str] = None
    bullets: List[str] = []

class SkillRow(BaseModel):
    label: str
    items: str

class ResumeData(BaseModel):
    header: Header
    education: List[EducationEntry] = []
    experience: List[ExperienceEntry] = []
    projects: List[ProjectEntry] = []
    skills: List[SkillRow] = []

    