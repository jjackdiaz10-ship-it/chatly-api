# app/schemas/learning_suggestion.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class LearningSuggestionBase(BaseModel):
    original_question: str
    ai_generated_answer: str
    confidence_score: float = 0.5
    status: str = "pending" # pending, approved, rejected

class LearningSuggestionUpdate(BaseModel):
    ai_generated_answer: Optional[str] = None
    status: Optional[str] = None # Para aprobar o rechazar

class LearningSuggestionOut(LearningSuggestionBase):
    id: int
    business_id: int
    created_at: datetime

    class Config:
        from_attributes = True
