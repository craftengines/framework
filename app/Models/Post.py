"""Post Model for Codepy Framework."""

from services.orm.model import Model


class Post(Model):
    __table__ = "posts"
    fillable = ["title", "body", "user_id", "published"]

    def user(self):
        from app.Models.User import User
        return self.belongs_to(User, foreign_key="user_id")

    @classmethod
    def scope_published(cls, query):
        return query.where("published", True)
