"""
app/models/category.py
───────────────────────
Self-referential category tree (parent → subcategories).

Example:
  Housing (parent)
    ├── Groceries   (child, parent_id = Housing.id)
    ├── Maid Salary
    └── Electricity
"""

from uuid import uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    parent_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    icon: Mapped[str | None] = mapped_column(String(20), nullable=True)
    color: Mapped[str | None] = mapped_column(String(9), nullable=True)

    # Self-referential relationships
    parent: Mapped["Category | None"] = relationship(
        "Category", remote_side="Category.id", back_populates="subcategories"
    )
    subcategories: Mapped[list["Category"]] = relationship(
        "Category", back_populates="parent", cascade="all, delete-orphan"
    )

    # Transactions that use this category
    transactions: Mapped[list["Transaction"]] = relationship(  # noqa: F821
        back_populates="category"
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r} parent_id={self.parent_id}>"
