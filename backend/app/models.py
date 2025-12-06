from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class ContainerModel(Base):
    __tablename__ = "containers"

    id = Column(Integer, primary_key=True, index=True)
    qr_code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)

    items = relationship(
        "ItemModel",
        back_populates="container",
        cascade="all, delete-orphan",
        order_by="ItemModel.id",
    )


class ItemModel(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    container_id = Column(Integer, ForeignKey("containers.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    details = Column(Text, nullable=True)

    container = relationship("ContainerModel", back_populates="items")
