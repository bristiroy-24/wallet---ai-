"""app/schemas/category.py – Category DTOs"""

from uuid import UUID

from pydantic import BaseModel


class CategoryRead(BaseModel):
    id: UUID
    name: str
    icon: str | None
    color: str | None
    parent_id: UUID | None
    subcategories: list["CategoryRead"] = []

    model_config = {"from_attributes": True}


# Allow self-referential type to resolve
CategoryRead.model_rebuild()
