"""Event service provider — register event listeners."""

from codepy.providers import ServiceProvider
from codepy.facades import Event


class EventServiceProvider(ServiceProvider):
    def register(self):
        pass

    def boot(self):
        from app.Events.PostPublished import PostPublished
        from app.Listeners.NotifySubscribers import NotifySubscribers
        Event.listen(PostPublished, [NotifySubscribers])
