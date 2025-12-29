from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, insert
from app.db.session import get_db
from app.db.association_tables import role_permissions
from app.schemas.role_permission import RolePermissionCreate, RolePermissionOut
from app.core.permissions import require_permission
from app.models.role import Role
from app.models.permission import Permission

from app.api.deps import get_current_user

router = APIRouter(prefix="/role_permissions", tags=["Role Permissions"])

@router.post("/", response_model=RolePermissionOut, dependencies=[Depends(require_permission("roles:update"))])
async def link_role_permission(
    data: RolePermissionCreate, 
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify role exists
    role = await db.get(Role, data.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Verify permission exists (Permissions are global)
    permission = await db.get(Permission, data.permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    # Check if already exists
    query = select(role_permissions).where(
        (role_permissions.c.role_id == data.role_id) & 
        (role_permissions.c.permission_id == data.permission_id)
    )
    result = await db.execute(query)
    if result.first():
        raise HTTPException(status_code=400, detail="Role already has this permission")

    # Insert into association table
    stmt = insert(role_permissions).values(role_id=data.role_id, permission_id=data.permission_id)
    await db.execute(stmt)
    await db.commit()
    
    return data

@router.get("/", response_model=list[RolePermissionOut], dependencies=[Depends(require_permission("roles:view"))])
async def list_role_permissions(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Roles and Permissions are currently global, so we just list them.
    # If roles become business-scoped, we would join with Role and filter by business_id.
    result = await db.execute(select(role_permissions))
    rows = result.all()
    return [{"role_id": r.role_id, "permission_id": r.permission_id} for r in rows]

@router.delete("/{role_id}/{permission_id}", dependencies=[Depends(require_permission("roles:update"))])
async def unlink_role_permission(
    role_id: int, 
    permission_id: int, 
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = delete(role_permissions).where(
        (role_permissions.c.role_id == role_id) & 
        (role_permissions.c.permission_id == permission_id)
    )
    result = await db.execute(stmt)
    await db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Association not found")
        
    return {"deleted": True}
