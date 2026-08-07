# Validation

## Validator

```python
from craft.validation import Validator

validator = Validator(request.all(), {
    "name":     ["required", "string", "max:255"],
    "email":    "required|email|unique:users,email",
    "age":      ["nullable", "integer", "between:18,120"],
    "password": ["required", "min:8", "confirmed"],
})

if validator.fails():
    return self.json({"errors": validator.errors}, status=422)

data = validator.validated()
```

Rules are a list or a pipe-delimited string — the two are equivalent.

`validated()` returns only the fields you wrote rules for, and raises
`ValidationException` if validation failed. Extra input the client sent is
dropped, so nothing unvalidated reaches your model.

## How rules are applied

Only `required*` rules run against a field that is absent or empty. Everything
else is skipped, so an optional field left blank does not report a type error.

`nullable` makes an explicit `None` acceptable.

## Available rules

**Presence**

| Rule | Passes when |
|---|---|
| `required` | Not `None`, `""`, `[]` or `{}` (zero passes) |
| `required_if:other,value` | Required only when `other` equals `value` |
| `required_with:a,b` | Required when any listed field is present |
| `nullable` | Allows an empty value |

**Types**

| Rule | Passes when |
|---|---|
| `string` | Value is a string |
| `integer` | An int or a numeric string. **Booleans fail** — `bool` subclasses `int` in Python, and accepting `True` as an integer is a bug |
| `numeric` | int, float, or a numeric string |
| `boolean` | `True`, `False`, `0`, `1`, `"0"`, `"1"`, `"true"`, `"false"` |
| `array` | A list or tuple |
| `date` | A date/datetime, or an ISO-8601 string |

**Formats**

`email`, `url`, `uuid`, `alpha`, `alpha_num`, `alpha_dash`,
`regex:<pattern>`.

**Size** — counts characters for strings, items for collections, and compares
the value itself for numbers.

`min:n`, `max:n`, `between:min,max`, `size:n`.

**Sets and comparisons**

| Rule | Passes when |
|---|---|
| `in:a,b,c` | Value is one of the list |
| `not_in:a,b` | Value is not in the list |
| `same:other` | Matches another field |
| `different:other` | Differs from another field |
| `confirmed` | Matches `<field>_confirmation` |
| `accepted` | `True`, `1`, `"on"`, `"yes"`, `"true"` |

**Database**

```python
"email": ["unique:users,email"]                 # no such row exists
"email": ["unique:users,email,{id},id"]         # ignoring the current record
"role_id": ["exists:roles,id"]                  # the row must exist
```

If no database is reachable these rules skip rather than rejecting valid data.

An unknown rule is ignored rather than failing the field.

## Results

```python
validator.passes()          # bool
validator.fails()           # bool
validator.errors            # {"email": ["Enter a valid email address."]}
validator.first_error()     # first message, any field
validator.first_error("email")
validator.error_messages()  # flat list
validator.validated()       # validated subset, or raises
```

## Custom messages

```python
Validator(data, {"name": ["required"]}, {"name": "Tell us your name."})
```

## FormRequest

Move rules and authorization next to the endpoint:

```python
# app/Http/Requests/StorePostRequest.py
from craft.validation import FormRequest


class StorePostRequest(FormRequest):
    def authorize(self) -> bool:
        return self.user() is not None

    def rules(self) -> dict:
        return {
            "title": ["required", "string", "max:255"],
            "body": ["required", "string"],
            "published": ["nullable", "boolean"],
        }

    def messages(self) -> dict:
        return {"title": "A title is required."}

    def prepare_for_validation(self, data: dict) -> dict:
        data = dict(data)
        if "title" in data:
            data["title"] = data["title"].strip()
        return data
```

```python
def store(self, request):
    data = StorePostRequest(request).validated()
    post = Post.create(data)
    return self.json(PostResource(post).to_array(), status=201)
```

`validated()` authorizes first — raising `AuthorizationException` (403) — then
validates, raising `ValidationException` (422). Both are rendered by the
exception handler.

> `validated()` used to return the request body untouched, so every rule
> declared on a FormRequest was silently ignored. If you are upgrading, expect
> requests that previously slipped through to now be rejected.

Inspect without raising:

```python
form = StorePostRequest(request)
if form.fails():
    return self.view("posts.create", {"errors": form.errors})
```

## Localized messages

Rule messages are English by default. Translate them through the catalog:

```python
from craft.support import __

{"email": __("validation.email")}
```

See [Localization](localization.md).
