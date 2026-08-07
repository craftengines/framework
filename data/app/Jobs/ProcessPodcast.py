"""ProcessPodcast — example queued job."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.queue import Job, ShouldQueue


class ProcessPodcast(Job, ShouldQueue):
    queue = "default"
    timeout = 120
    tries = 3

    def __init__(self, podcast_id):
        self.podcast_id = podcast_id

    def handle(self):
        # Process the podcast...
        pass
