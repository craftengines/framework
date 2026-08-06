"""Database seeder — runs all seeders."""

from codepy.seeding import Seeder
from database.seeders.UserSeeder import UserSeeder
from database.seeders.PostSeeder import PostSeeder
from database.seeders.FrameworkSeeder import FrameworkSeeder


class DatabaseSeeder(Seeder):
    def run(self):
        self.call(UserSeeder)
        self.call(PostSeeder)
        self.call(FrameworkSeeder)
