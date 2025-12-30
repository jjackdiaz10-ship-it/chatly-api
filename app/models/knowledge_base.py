# app/models/knowledge_base.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float
from app.db.base_class import Base

class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    
    question = Column(String, nullable=False)
    answer = Column(Text, nullable=False)
    
    category = Column(String, default="general") # e.g., "shipping", "refunds", "sizes"
    
    # Optional: For future embedding-based search
    vector_id = Column(String, nullable=True) 
