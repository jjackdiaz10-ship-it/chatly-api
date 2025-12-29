from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.api.deps import get_current_user
from app.core.permissions import require_permission
from app.models.business_user import BusinessUser

def generate_crud(
    *,
    model,
    schema_create,
    schema_update,
    prefix: str,
    tag: str,
    permissions: dict = None
) -> APIRouter:

    router = APIRouter(prefix=prefix, tags=[tag])
    
    if permissions is None:
        permissions = {}

    def get_deps(action: str):
        perm_code = permissions.get(action)
        if perm_code:
            return [Depends(require_permission(perm_code))]
        return []

    # Crear
    @router.post("/", dependencies=get_deps("create"))
    async def create(
        data: schema_create, 
        user = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        data_dict = data.model_dump(exclude_unset=True)
        
        # If model has business_id field
        if hasattr(model, "business_id"):
            b_id = data_dict.get("business_id")
            
            # If not provided, try to get from user's first membership
            if not b_id:
                res = await db.execute(
                    select(BusinessUser).where(BusinessUser.user_id == user.id)
                )
                membership = res.scalars().first()
                if membership:
                    b_id = membership.business_id
                    data_dict["business_id"] = b_id
            
            # Validate membership (unless Admin)
            if b_id and user.role.name != "Admin":
                res = await db.execute(
                    select(BusinessUser).where(
                        BusinessUser.user_id == user.id,
                        BusinessUser.business_id == b_id
                    )
                )
                if not res.scalar_one_or_none():
                    raise HTTPException(status_code=403, detail="Not a member of this business")
            
        obj = model(**data_dict)
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    # Listar / Leer
    @router.get("/", dependencies=get_deps("read"))
    async def list(
        user = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        query = select(model)
        
        # If user is Admin, they see everything. 
        # If not Admin, filter by their memberships.
        if user.role.name != "Admin":
            # Get user's business IDs
            mem_res = await db.execute(
                select(BusinessUser.business_id).where(BusinessUser.user_id == user.id)
            )
            business_ids = mem_res.scalars().all()
            
            if hasattr(model, "business_id"):
                query = query.where(model.business_id.in_(business_ids))
            elif model.__name__ == "Business":
                query = query.where(model.id.in_(business_ids))
            
        result = await db.execute(query)
        return result.scalars().all()

    # Actualizar
    @router.put("/{id}", dependencies=get_deps("update"))
    async def update(
        id: int, 
        data: schema_update, 
        user = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        query = select(model).where(model.id == id)
        
        # Security check for business_id
        if hasattr(model, "business_id") and user.role.name != "Admin":
            query = query.join(
                BusinessUser, 
                (model.business_id == BusinessUser.business_id) & (BusinessUser.user_id == user.id)
            )
            
        result = await db.execute(query)
        obj = result.scalar_one_or_none()
        
        if not obj:
            raise HTTPException(status_code=404, detail="Not found or access denied")
            
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        await db.commit()
        return obj

    # Eliminar
    @router.delete("/{id}", dependencies=get_deps("delete"))
    async def delete(
        id: int, 
        user = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        query = select(model).where(model.id == id)
        
        # Security check for business_id
        if hasattr(model, "business_id") and user.role.name != "Admin":
            query = query.join(
                BusinessUser, 
                (model.business_id == BusinessUser.business_id) & (BusinessUser.user_id == user.id)
            )
            
        result = await db.execute(query)
        obj = result.scalar_one_or_none()
        
        if not obj:
            raise HTTPException(status_code=404, detail="Not found or access denied")
            
        await db.delete(obj)
        await db.commit()
        return {"deleted": True}

    return router
