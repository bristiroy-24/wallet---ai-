"""
app/db/seed.py
───────────────
Seeds the database with default categories on first run.

Category names here are the CANONICAL source of truth.
All other files must match exactly:
  - frontend: js/config.js (SUBCATEGORIES, CATEGORY_EMOJI)
  - frontend: index.html   (category <select> options)
  - frontend: js/ai.js     (mockParseNaturalLanguage)
  - backend:  app/services/mock_ai_service.py (_CATEGORY_KEYWORDS)
"""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category


# ── Canonical category list ───────────────────────────────────────────────────
# Format: (name, icon, hex_color, [subcategory_names])
DEFAULT_CATEGORIES = [
    ("Food & Drinks",          "🍔", "#EF4444", [
        "Restaurant", "Zomato / Swiggy", "Cafe / Coffee", "Grocery", "Other",
    ]),
    ("Shopping",               "🛍️", "#EC4899", [
        "Clothing", "Electronics", "Amazon / Flipkart", "Myntra", "Personal Care", "Other",
    ]),
    ("Housing",                "🏠", "#F59E0B", [
        "Groceries", "Maid Salary", "Electricity", "Water", "Gas", "Internet / Wi-Fi", "Maintenance",
    ]),
    ("Entertainment",          "🎬", "#A855F7", [
        "Netflix", "Amazon Prime", "Spotify", "Disney+", "YouTube Premium", "Gaming", "Other",
    ]),
    ("Recharge",               "📱", "#3B82F6", [
        "Phone Recharge", "Wi-Fi Bill", "DTH / Cable", "Other",
    ]),
    ("Education",              "📚", "#22C55E", [
        "Books", "Courses", "Tuition", "Other",
    ]),
    ("Transport",              "🚗", "#14B8A6", [
        "Fuel", "Ola / Uber", "Metro / Bus", "Auto", "Flight / Train", "Other",
    ]),
    ("Health",                 "💊", "#F97316", [
        "Doctor", "Pharmacy", "Hospital", "Insurance", "Other",
    ]),
    ("Investments",            "💰", "#8B5CF6", [
        "Stocks", "Mutual Funds", "Fixed Deposit", "Crypto", "Other",
    ]),
    ("Lifestyle",              "🙎", "#F43F5E", [
        "Gym", "Salon", "Dining Out", "Travel", "Hobbies", "Other",
    ]),
    ("Other",                  "📦", "#64748B", []),
]


async def seed_categories(db: AsyncSession) -> None:
    """
    Idempotent seed — inserts default categories only if the table is empty.
    """
    result = await db.execute(select(Category).limit(1))
    if result.scalar_one_or_none() is not None:
        return  # Already seeded

    for name, icon, color, subs in DEFAULT_CATEGORIES:
        parent = Category(id=uuid4(), name=name, icon=icon, color=color)
        db.add(parent)
        await db.flush()  # assigns parent.id before inserting children

        for sub_name in subs:
            db.add(Category(
                id=uuid4(), name=sub_name, icon=icon,
                color=color, parent_id=parent.id,
            ))

    await db.commit()
