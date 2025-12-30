# app/api/v1/knowledge_base.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.session import get_db
from app.models.knowledge_base import KnowledgeBase
from app.schemas.knowledge_base import KnowledgeBaseOut, KnowledgeBaseCreate, KnowledgeBaseUpdate
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])

@router.get("/{business_id}", response_model=List[KnowledgeBaseOut])
async def list_kb_items(
    business_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(KnowledgeBase).where(KnowledgeBase.business_id == business_id)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/", response_model=KnowledgeBaseOut)
async def create_kb_item(
    data: KnowledgeBaseCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = KnowledgeBase(**data.dict())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.patch("/{item_id}", response_model=KnowledgeBaseOut)
async def update_kb_item(
    item_id: int, 
    data: KnowledgeBaseUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = await db.get(KnowledgeBase, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    for field, value in data.dict(exclude_unset=True).items():
        setattr(item, field, value)
        
    await db.commit()
    await db.refresh(item)
    return item

@router.delete("/{item_id}")
async def delete_kb_item(
    item_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = await db.get(KnowledgeBase, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()
    return {"status": "ok"}
