"""Database seeder — runs all seeders."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from codepy.seeding import Seeder
from database.seeders.UserSeeder import UserSeeder
from database.seeders.PostSeeder import PostSeeder
from database.seeders.FrameworkSeeder import FrameworkSeeder


class DatabaseSeeder(Seeder):
    def run(self):
        self.call(UserSeeder)
        self.call(PostSeeder)
        self.call(FrameworkSeeder)
