"""NotifySubscribers listener."""

from codepy.facades import Log


class NotifySubscribers:
    def handle(self, event):
        Log.info("New post published: %s", event.post.get_attribute("title"))
