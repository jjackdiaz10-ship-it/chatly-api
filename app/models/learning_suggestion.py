# app/models/learning_suggestion.py
from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.sql import func
from app.db.base_class import Base

class LearningSuggestion(Base):
    __tablename__ = "learning_suggestions"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, index=True)
    original_question = Column(String, nullable=False)
    ai_generated_answer = Column(String, nullable=False)
    confidence_score = Column(Float, default=1.0)
    status = Column(String, default="pending") # pending, approved, rejected
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
