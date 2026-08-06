"""Policy for Post authorization."""

class PostPolicy:
    def view_any(self, user):
        return True

    def view(self, user, post):
        return True

    def create(self, user):
        return user is not None

    def update(self, user, post):
        if user is None:
            return False
        return user.get_attribute("id") == post.get_attribute("user_id") or user.get_attribute("is_admin")

    def delete(self, user, post):
        if user is None:
            return False
        return user.get_attribute("id") == post.get_attribute("user_id") or user.get_attribute("is_admin")
