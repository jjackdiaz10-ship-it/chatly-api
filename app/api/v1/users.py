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


@router.get("/me", response_model=UserRead)
async def read_user_me(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user profile with active business context.
    """
    # Force load memberships to ensure we get the business_id
    # (Although deps.py might validly load it, we ensure here)
    if not current_user.memberships:
        # Re-fetch or assuming deps.py loaded it with selectinload
        pass

    # Logic to pick primary business (for now, simply the first one)
    if current_user.memberships and len(current_user.memberships) > 0:
        # Pydantic will not auto-fill this dynamic field from the ORM model unless it's a property
        # So we create a dictionary or modify the object if it's a Pydantic model
        # But current_user is an ORM object.
        # Safest way: Attach the attribute manually to the ORM instance (it's dirty but works for Pydantic from_attributes)
        current_user.business_id = current_user.memberships[0].business_id
    
    return current_user


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
