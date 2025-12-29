# app/db/association_tables.py
from sqlalchemy import Table, Column, Integer, ForeignKey
from app.db.base_class import Base

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id"), primary_key=True),
)
