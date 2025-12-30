from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    refresh_token_expiry
)
from sqlalchemy.orm import selectinload
from app.schemas.login import LoginResponseSchema, TokenSchema
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="User login",
    response_model=LoginResponseSchema
)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user credentials and issue access & refresh tokens.
    """

    # 1️⃣ Buscar usuario + rol (evita lazy-loading)
    stmt = (
        select(User)
        .options(selectinload(User.role), selectinload(User.memberships))
        .where(User.email == form.username)
    )

    result = await db.execute(stmt)
    user: User | None = result.scalar_one_or_none()

    # 2️⃣ Validación genérica (evita user enumeration)
    if not user or not verify_password(form.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )

    # 3️⃣ Crear access token (JWT corto)
    access_token = create_access_token(
        payload={
            "sub": str(user.id),
            "role": user.role.name
        }
    )

    # 4️⃣ Crear refresh token (largo + persistido)
    refresh_token = create_refresh_token()
    refresh_expires_at = refresh_token_expiry()

    db.add(
        RefreshToken(
            token=refresh_token,
            user_id=user.id,
            expires_at=refresh_expires_at
        )
    )
    await db.commit()

    # 5️⃣ Respuesta profesional para frontend
    # Get business_id from first membership if exists
    business_id = None
    if user.memberships and len(user.memberships) > 0:
        business_id = user.memberships[0].business_id
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.name,
            "business_id": business_id
        }
    }


@router.post("/refresh")
async def refresh_token(req: TokenSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RefreshToken)
        .where(
            RefreshToken.token == req.token,
            RefreshToken.revoked == False
        )
    )
    rt = result.scalar_one_or_none()

    if not rt or rt.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token inválido o expirado")

    # Cargar usuario con su rol
    stmt = (
        select(User)
        .options(selectinload(User.role))
        .where(User.id == rt.user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role.name
    })

    return {"access_token": access_token}

@router.post("/logout")
async def logout(req: TokenSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == req.token)
    )
    rt = result.scalar_one_or_none()

    if rt:
        rt.revoked = True
        await db.commit()

    return {"detail": "Sesión cerrada"}