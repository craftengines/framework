"""NotifySubscribers listener."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from codepy.facades import Log


class NotifySubscribers:
    def handle(self, event):
        Log.info("New post published: %s", event.post.get_attribute("title"))
