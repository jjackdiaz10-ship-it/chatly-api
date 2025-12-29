# app/api/v1/carts.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.db.session import get_db
from app.models.cart import Cart, CartItem
from app.schemas.cart import CartOut, CartUpdate, CartCreate
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/carts", tags=["Carts"])

@router.get("/", response_model=List[CartOut])
async def list_carts(
    business_id: Optional[int] = None, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Determinar el business_id si no se provee
    if business_id is None:
        if not current_user.memberships:
            raise HTTPException(status_code=400, detail="El usuario no pertenece a ningún negocio")
        business_id = current_user.memberships[0].business_id
    else:
        # 2. Verificar que el usuario tenga acceso a ese negocio (si no es Admin)
        is_admin = current_user.role.name == "Admin"
        user_biz_ids = [m.business_id for m in current_user.memberships]
        if not is_admin and business_id not in user_biz_ids:
            raise HTTPException(status_code=403, detail="No tienes permiso para ver carritos de este negocio")

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
