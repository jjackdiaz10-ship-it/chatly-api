# app/api/v1/carts.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import List
from app.db.session import get_db
from app.models.cart import Cart, CartItem
from app.schemas.cart import CartOut, CartUpdate, CartCreate
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/carts", tags=["Carts"])

@router.get("/", response_model=List[CartOut])
async def list_carts(
    business_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # TODO: Verify current_user belongs to business_id
    stmt = select(Cart).where(Cart.business_id == business_id).options(
        selectinload(Cart.items).selectinload(CartItem.product)
    ).order_by(Cart.created_at.desc())
    
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/{cart_id}", response_model=CartOut)
async def get_cart(
    cart_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Cart).where(Cart.id == cart_id).options(
        selectinload(Cart.items).selectinload(CartItem.product)
    )
    res = await db.execute(stmt)
    cart = res.scalar_one_or_none()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    return cart

@router.patch("/{cart_id}", response_model=CartOut)
async def update_cart(
    cart_id: int, 
    data: CartUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Cart).where(Cart.id == cart_id).options(
        selectinload(Cart.items).selectinload(CartItem.product)
    )
    res = await db.execute(stmt)
    cart = res.scalar_one_or_none()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    if data.is_active is not None:
        cart.is_active = data.is_active
    if data.metadata_json is not None:
        cart.metadata_json = data.metadata_json
        
    await db.commit()
    await db.refresh(cart)
    return cart

@router.delete("/{cart_id}")
async def delete_cart(
    cart_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Cart).where(Cart.id == cart_id)
    res = await db.execute(stmt)
    cart = res.scalar_one_or_none()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    await db.delete(cart)
    await db.commit()
    return {"status": "ok"}
