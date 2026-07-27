"""Seed the categories table with vehicle types."""

CATEGORIES = [
    {"slug": "car", "title": "Автомобиль", "icon": "car", "sort_order": 1},
    {"slug": "car-sedan", "title": "Легковой", "icon": "car", "parent_slug": "car", "sort_order": 1},
    {"slug": "car-truck", "title": "Грузовой", "icon": "truck", "parent_slug": "car", "sort_order": 2},
    {"slug": "tractor", "title": "Трактор / сельхоз", "icon": "tractor", "sort_order": 2},
    {"slug": "trailer", "title": "Прицеп / полуприцеп", "icon": "trailer", "sort_order": 3},
    {"slug": "motorcycle", "title": "Мотоцикл / мопед", "icon": "motorcycle", "sort_order": 4},
    {"slug": "combine", "title": "Комбайн", "icon": "combine", "sort_order": 5},
    {"slug": "bus", "title": "Автобус / микроавтобус", "icon": "bus", "sort_order": 6},
    {"slug": "special", "title": "Спецтехника", "icon": "special", "sort_order": 7},
    {"slug": "other", "title": "Другое", "icon": "other", "sort_order": 8},
]


def seed_categories():
    from app import create_app
    from app.extensions import db
    from app.models.category import Category

    app = create_app()
    with app.app_context():
        existing = Category.query.count()
        if existing > 0:
            print(f"Categories already seeded ({existing} found). Skipping.")
            return

        slug_to_id = {}
        for cat_data in CATEGORIES:
            parent_id = slug_to_id.get(cat_data.get("parent_slug"))
            cat = Category(
                slug=cat_data["slug"],
                title=cat_data["title"],
                icon=cat_data.get("icon", "other"),
                parent_id=parent_id,
                sort_order=cat_data.get("sort_order", 0),
            )
            db.session.add(cat)
            db.session.flush()
            slug_to_id[cat_data["slug"]] = cat.id

        db.session.commit()
        print(f"Seeded {len(CATEGORIES)} categories.")


if __name__ == "__main__":
    seed_categories()
