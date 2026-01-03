# app/api/v1/learning.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.session import get_db
from app.models.learning_suggestion import LearningSuggestion
from app.models.knowledge_base import KnowledgeBase
from app.schemas.learning_suggestion import LearningSuggestionOut, LearningSuggestionUpdate
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/learning", tags=["AI Learning System"])

@router.get("/suggestions/{business_id}", response_model=List[LearningSuggestionOut])
async def list_suggestions(
    business_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista las sugerencias de aprendizaje pendientes para un negocio."""
    stmt = select(LearningSuggestion).where(
        LearningSuggestion.business_id == business_id,
        LearningSuggestion.status == "pending"
    ).order_by(LearningSuggestion.created_at.desc())
    
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/suggestions/{suggestion_id}/approve", response_model=dict)
async def approve_suggestion(
    suggestion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Aprueba una sugerencia y la convierte en una FAQ oficial en la KnowledgeBase."""
    suggestion = await db.get(LearningSuggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Sugerencia no encontrada")
    
    # 1. Crear el ítem en la KnowledgeBase
    new_kb_item = KnowledgeBase(
        business_id=suggestion.business_id,
        question=suggestion.original_question,
        answer=suggestion.ai_generated_answer
    )
    db.add(new_kb_item)
    
    # 2. Marcar sugerencia como aprobada
    suggestion.status = "approved"
    
    await db.commit()
    return {"status": "success", "message": "Sugerencia approved y añadida a la KnowledgeBase"}

@router.patch("/suggestions/{suggestion_id}", response_model=LearningSuggestionOut)
async def update_suggestion(
    suggestion_id: int,
    data: LearningSuggestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Permite editar la respuesta de la IA antes de aprobarla o simplemente rechazarla."""
    suggestion = await db.get(LearningSuggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Sugerencia no encontrada")
    
    for field, value in data.dict(exclude_unset=True).items():
        setattr(suggestion, field, value)
        
    await db.commit()
    await db.refresh(suggestion)
    return suggestion

@router.delete("/suggestions/{suggestion_id}")
async def reject_suggestion(
    suggestion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rechaza y elimina una sugerencia de la lista."""
    suggestion = await db.get(LearningSuggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Sugerencia no encontrada")
    
    await db.delete(suggestion)
    await db.commit()
    return {"status": "ok", "message": "Sugerencia eliminada"}
