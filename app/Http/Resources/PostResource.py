"""Post API resource — transforms Post models for JSON output."""

from codepy.resources import Resource


class PostResource(Resource):
    def to_array(self, request=None):
        post = self.resource
        return {
            "id": post.get_attribute("id"),
            "title": post.get_attribute("title"),
            "body": post.get_attribute("body"),
            "published": post.get_attribute("published"),
            "created_at": str(post.get_attribute("created_at")) if post.get_attribute("created_at") else None,
            "updated_at": str(post.get_attribute("updated_at")) if post.get_attribute("updated_at") else None,
        }
