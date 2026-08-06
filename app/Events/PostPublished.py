"""PostPublished event."""

from codepy.events import Event


class PostPublished(Event):
    def __init__(self, post):
        self.post = post
