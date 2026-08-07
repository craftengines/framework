"""FormRequest for creating/updating posts."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Auth
from craft.validation import FormRequest


class StorePostRequest(FormRequest):
    def authorize(self):
        # Ownership (update vs. create-only) is enforced separately in the
        # controller via `Gate.authorize` against `PostPolicy` — this only
        # rejects anonymous submissions before validation runs.
        return Auth.user() is not None

    def rules(self):
        return {
            "title": ["required", "string", "max:255"],
            "body": ["required", "string"],
            "published": ["nullable", "boolean"],
        }

    def messages(self):
        return {
            "title.required": "A title is required.",
            "body.required": "The post body cannot be empty.",
        }
