# app/schemas/knowledge_base.py
from pydantic import BaseModel
from typing import Optional

class KnowledgeBaseBase(BaseModel):
    question: str
    answer: str
    category: Optional[str] = "general"

class KnowledgeBaseCreate(KnowledgeBaseBase):
    business_id: int

class KnowledgeBaseUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None

class KnowledgeBaseOut(KnowledgeBaseBase):
    id: int
    business_id: int
    class Config:
        from_attributes = True
