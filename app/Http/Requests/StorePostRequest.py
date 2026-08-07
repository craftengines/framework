"""FormRequest for creating/updating posts."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.validation import FormRequest


class StorePostRequest(FormRequest):
    def authorize(self):
        return True

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
