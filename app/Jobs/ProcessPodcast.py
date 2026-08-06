"""ProcessPodcast — example queued job."""

from codepy.queue import Job, ShouldQueue


class ProcessPodcast(Job, ShouldQueue):
    queue = "default"
    timeout = 120
    tries = 3

    def __init__(self, podcast_id):
        self.podcast_id = podcast_id

    def handle(self):
        # Process the podcast...
        pass
