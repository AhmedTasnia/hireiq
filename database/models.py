from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

Base = declarative_base()
DB_PATH = os.path.join(os.path.dirname(__file__), "hireiq.db")

class Session_DB(Base):
    __tablename__ = "screening_sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_title = Column(String(200))
    circular_text = Column(Text)
    extracted_criteria = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer)
    name = Column(String(200))
    email = Column(String(200))
    phone = Column(String(50))
    cv_path = Column(String(500))
    cv_text = Column(Text)
    total_score = Column(Float, default=0.0)
    score_breakdown = Column(JSON)
    rank = Column(Integer)
    status = Column(String(50), default="pending")  # pending / selected / rejected / hold
    interview_transcript = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

def get_engine():
    return create_engine(f"sqlite:///{DB_PATH}", echo=False)

def get_session():
    engine = get_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
