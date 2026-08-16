"""
app/db/seed.py
───────────────
Seeds the database with default categories on first run.
Call this from the startup event in main.py.
"""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category


DEFAULT_CATEGORIES = [
    # (name, icon, color, subcategories)
    ("Food & Drinks", "🍔", "#EF4444", ["Restaurant", "Zomato / Swiggy", "Cafe / Coffee", "Grocery"]),
    ("Shopping",      "🛍️", "#EC4899", ["Clothing", "Electronics", "Amazon / Flipkart", "Personal Care"]),
    ("Housing",       "🏠", "#F59E0B", ["Groceries", "Maid Salary", "Electricity", "Water", "Gas", "Maintenance"]),
    ("Entertainment", "🎬", "#A855F7", ["Netflix", "Amazon Prime", "Spotify", "Disney+", "Gaming"]),
    ("Recharge",      "📱", "#3B82F6", ["Phone Recharge", "Wi-Fi Bill", "DTH / Cable"]),
    ("Education",     "📚", "#22C55E", ["Books", "Courses", "Tuition"]),
    ("Transport",     "🚗", "#14B8A6", ["Fuel", "Ola / Uber", "Metro / Bus", "Auto", "Flight / Train"]),
    ("Health",        "💊", "#F97316", ["Doctor", "Pharmacy", "Hospital", "Insurance"]),
    ("Other",         "📦", "#64748B", []),
]


async def seed_categories(db: AsyncSession) -> None:
    """
    Idempotent seed: inserts default categories only if the
    categories table is empty.
    """
    result = await db.execute(select(Category).limit(1))
    if result.scalar_one_or_none() is not None:
        return  # Already seeded

    for name, icon, color, subs in DEFAULT_CATEGORIES:
        parent = Category(id=uuid4(), name=name, icon=icon, color=color)
        db.add(parent)
        await db.flush()  # get parent.id without committing

        for sub_name in subs:
            child = Category(
                id=uuid4(),
                name=sub_name,
                icon=icon,
                color=color,
                parent_id=parent.id,
            )
            db.add(child)

    await db.commit()
