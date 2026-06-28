from sqlalchemy import Column, String, Integer, Boolean, Float, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
import uuid
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False) # 🌟 NEW: To store passwords safely
    name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    preferences = Column(JSON, default={})

class MasterResume(Base):
    __tablename__ = "master_resumes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True)
    raw_file_url = Column(String)  # MinIO path to original PDF
    parsed_json = Column(JSON)     # Structured Resume Data
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CuratedResume(Base):
    __tablename__ = "curated_resumes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    master_resume_id = Column(UUID(as_uuid=True), ForeignKey("master_resumes.id"))
    jd_snapshot = Column(JSON)
    ats_score = Column(Float)
    pdf_url = Column(String)
    docx_url = Column(String)
    template = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True) # Hash of title+company+location
    title = Column(String)
    company = Column(String)
    location = Column(String)
    remote = Column(Boolean)
    job_type = Column(String)
    jd_text = Column(String)
    apply_url = Column(String)
    source = Column(String)
    posted_at = Column(DateTime(timezone=True))
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    embedding_id = Column(String) # Ref to Vector DB later

class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    curated_resume_id = Column(UUID(as_uuid=True), ForeignKey("curated_resumes.id"))
    jd_snapshot = Column(JSON)
    mode = Column(String)
    status = Column(String, default='in_progress')
    question_bank = Column(JSON)
    evaluations = Column(JSON)
    overall_score = Column(Float)
    debrief_url = Column(String)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True))

class Application(Base):
    __tablename__ = "applications"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    title = Column(String)
    company = Column(String)
    location = Column(String)
    apply_url = Column(String)
    status = Column(String, default="saved") # saved, applied, interviewing, offer, rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SavedSearch(Base):
    __tablename__ = "saved_searches"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    keyword = Column(String)
    location = Column(String)
    slack_channel_id = Column(String) 
    seen_jobs = Column(JSON, default=list) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())