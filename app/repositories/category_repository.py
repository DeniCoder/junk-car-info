from app.extensions import db
from app.models.category import Category


class CategoryRepository:

    @staticmethod
    def get_all():
        return Category.query.filter_by(parent_id=None).order_by(Category.sort_order).all()

    @staticmethod
    def get_by_id(cat_id):
        return db.session.get(Category, cat_id)

    @staticmethod
    def get_by_slug(slug):
        return Category.query.filter_by(slug=slug).first()

    @staticmethod
    def get_all_flat():
        return Category.query.order_by(Category.sort_order).all()
