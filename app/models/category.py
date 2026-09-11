from app.extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(64), unique=True, nullable=False, index=True)
    title = db.Column(db.String(128), nullable=False)
    icon = db.Column(db.String(32), nullable=False, default="other")
    parent_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)

    parent = db.relationship("Category", remote_side=[id], backref="children")
    findings = db.relationship("Finding", backref="category", lazy="dynamic")

    def to_dict(self):
        d = {
            "id": self.id,
            "slug": self.slug,
            "title": self.title,
            "icon": self.icon,
            "parent_id": self.parent_id,
            "sort_order": self.sort_order,
        }
        if self.children:
            d["children"] = [c.to_dict() for c in sorted(self.children, key=lambda x: x.sort_order)]
        return d

    def __repr__(self):
        return f"<Category {self.slug}>"
