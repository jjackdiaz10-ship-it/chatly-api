from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.models.permission import Permission
from app.db.association_tables import role_permissions

def require_permission(permission_code: str):
    async def checker(
        user = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        if not user.role_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario sin rol asignado"
            )

        print("USURIO ROLE: ", user.role_id)

        query = select(role_permissions).join(
            Permission,
            role_permissions.c.permission_id == Permission.id
        ).where(
            role_permissions.c.role_id == user.role_id,
            Permission.code == permission_code
        )


        result = await db.execute(query)
        role_perm = result.first()
        print("PERMISO CODE: ", permission_code)
        print("PERMISO: ", role_perm)

        if not role_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos"
            )

        return user
    return checker  # 🔑 retornamos la función, no la corutina
