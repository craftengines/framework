"""NotifySubscribers listener."""

from codepy.facades import Log


class NotifySubscribers:
    def handle(self, event):
        try:
            Log.info(f"New post published: {event.post.get_attribute('title')}")
        except Exception:
            pass
