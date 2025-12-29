from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str | None]
    business_id: Mapped[int | None] = mapped_column(ForeignKey("businesses.id"))
    business_channels = relationship("BusinessChannel", back_populates="channel")
