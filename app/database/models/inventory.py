from __future__ import annotations

import datetime as dt

from sqlalchemy import String, Integer, Float, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.config.constants import ItemStatus


class InventoryCategory(Base):
    __tablename__ = "inventory_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    sync_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    last_modified_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    remote_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    items: Mapped[list["InventoryItem"]] = relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<InventoryCategory {self.name}>"


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("inventory_categories.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=0)
    minimum_quantity: Mapped[float] = mapped_column(Float, default=0)
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    expiry_date: Mapped[dt.date | None] = mapped_column(Date)
    supplier: Mapped[str | None] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default=ItemStatus.ACTIVE)
    sync_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    last_modified_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    remote_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    category: Mapped["InventoryCategory"] = relationship(back_populates="items")
    transactions: Mapped[list["InventoryTransaction"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )

    @property
    def is_low_stock(self) -> bool:
        return self.quantity <= self.minimum_quantity

    def __repr__(self) -> str:
        return f"<InventoryItem {self.code}>"


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id"), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    transaction_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(100))
    note: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    sync_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    last_modified_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    remote_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    item: Mapped["InventoryItem"] = relationship(back_populates="transactions")

    def __repr__(self) -> str:
        return f"<InventoryTransaction {self.transaction_type} qty={self.quantity}>"
