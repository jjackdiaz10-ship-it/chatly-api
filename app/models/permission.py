# app/models/permission.py
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from app.db.association_tables import role_permissions
from sqlalchemy import Column, Integer, String

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True)
    code = Column(String)

    roles = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions"
    )
