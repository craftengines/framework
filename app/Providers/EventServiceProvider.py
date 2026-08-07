"""Event service provider — register event listeners."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.providers import ServiceProvider
from craft.facades import Event


class EventServiceProvider(ServiceProvider):
    def register(self):
        pass

    def boot(self):
        from app.Events.PostPublished import PostPublished
        from app.Listeners.NotifySubscribers import NotifySubscribers
        Event.listen(PostPublished, [NotifySubscribers])
