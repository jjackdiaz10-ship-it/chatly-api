# app/api/v1/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.role import Role
from app.schemas.user import UserCreate, UserRead
from app.core.security import hash_password
from app.api.deps import get_current_user
from app.core.permissions import require_permission
from app.models.business_user import BusinessUser

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("users:create"))]
)
async def create_user(
    data: UserCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verificar email único
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Email ya registrado"
        )

    # Verificar rol existente
    role = await db.get(Role, data.role_id)
    if not role:
        raise HTTPException(
            status_code=400,
            detail="Rol no existe"
        )

    user = User(
        email=data.email,
        password=hash_password(data.password),
        role_id=data.role_id,
        is_active=data.is_active
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.get(
    "/",
    response_model=list[UserRead],
    dependencies=[Depends(require_permission("users:view"))]
)
async def list_users(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role.name == "Admin":
        result = await db.execute(select(User))
    else:
        # Usuarios que comparten al menos un negocio con el usuario actual
        user_businesses = select(BusinessUser.business_id).where(BusinessUser.user_id == current_user.id)
        result = await db.execute(
            select(User)
            .join(BusinessUser, User.id == BusinessUser.user_id)
            .where(BusinessUser.business_id.in_(user_businesses))
            .distinct()
        )
    return result.scalars().all()
