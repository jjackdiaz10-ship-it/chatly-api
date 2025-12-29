# app/models/role.py
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from app.db.association_tables import role_permissions
from sqlalchemy import Column, Integer, String

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String)

    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles"
    )
