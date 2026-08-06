"""PostPublished event."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from codepy.events import Event


class PostPublished(Event):
    def __init__(self, post):
        self.post = post
