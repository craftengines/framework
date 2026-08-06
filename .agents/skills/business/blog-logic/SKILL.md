---
name: codepy-blog-business-rules
description: Business logic and validation rules for the Codepy demo blog application (app/ directory).
---

# Codepy Blog Business Rules (Business Skill)

This skill governs the domain-specific business rules for the blog application code located in the `app/` directory.

---

## 1. Authentication & Security

* **Hashing:** Passwords must be hashed using the `Hasher` facade (`Hasher.make()`) prior to saving in the database.
* **Authentication Guards:** Web controllers use session guard authentication, while API controllers use token-based validation.

---

## 2. Model Specific Rules

### User Model
* A user contains attributes: `name`, `email`, `password`, `is_admin`.
* The `password` attribute must always be hidden in JSON responses.
* Access control: Only users marked as `is_admin` can execute administrative backend tasks.

### Post Model
* A post is authored by a single `User`.
* Content validation:
  * Title is required, must be a string, and cannot exceed 255 characters.
  * Body is required, must be a string, and must be at least 10 characters long.
  * Authorship: A post's `user_id` must match the currently authenticated user's ID.
  * Modification: Only the author of the post or an administrator can update or delete a post.
