# Localization

Locales follow **BCP 47**: a lowercase language subtag, optionally followed by
an uppercase region subtag — `en`, `pt`, `pt-BR`, `es`.

## Translating

```python
from codepy.support import __

__("login")                    # active locale
__("login", "pt-BR")           # a specific locale
__("welcome_{name}", "pt-BR", name="Ana")
```

In templates:

```html
<h1>{{ __('recent_posts') }}</h1>
```

A key with no translation returns the key itself, so a missing string is visible
rather than blank.

## The fallback chain

A regional locale inherits from its base language, then from the application
fallback:

```
pt-BR  →  pt  →  en
```

```python
from codepy.support import locale_chain

locale_chain("pt-BR", "en")   # ['pt-BR', 'pt', 'en']
locale_chain("pt", "en")      # ['pt', 'en']
```

This means a regional locale only needs the keys where it genuinely differs.
Ask for `pt-BR` and get `pt` when the Brazilian variant has nothing to add.

Configure the ends of the chain:

```ini
APP_LOCALE=pt-BR
APP_FALLBACK_LOCALE=en
```

## Casing

Tags are normalised, so lookups are case-insensitive and underscore-tolerant:

```python
from codepy.support import normalize_locale

normalize_locale("PT-br")   # 'pt-BR'
normalize_locale("pt_BR")   # 'pt-BR'
normalize_locale("EN")      # 'en'
```

Store the canonical form; the helper accepts the rest.

## Where translations live

Two sources, checked in this order per locale in the chain:

**1. Configuration** — for values that ship with the code:

```python
# config/lang.py
pt_BR = {"greeting": "Olá"}
```

```python
Config.set("lang.pt-BR.greeting", "Olá")
```

**2. The `translations` table** — for values that change without a deploy:

| key | locale | value |
|---|---|---|
| `login` | `pt-BR` | Entrar |
| `login` | `pt` | Iniciar sessão |

Seed them in `database/seeders/TranslationSeeder.py`:

```python
TRANSLATIONS = {
    "en": {"login": "Log In", "dashboard": "Dashboard"},
    "pt": {"login": "Iniciar sessão", "dashboard": "Painel de Controlo"},
    "pt-BR": {"login": "Entrar", "dashboard": "Painel de Controle"},
    "es": {"login": "Iniciar sesión", "dashboard": "Panel de Control"},
}
```

```bash
python craft.py db seed
```

## pt and pt-BR are not the same

They are different copy, not a relabel. Filing Brazilian text under the generic
`pt` tag means European Portuguese users get the wrong words.

| Key | `pt` | `pt-BR` |
|---|---|---|
| `dashboard` | Painel de Controlo | Painel de Controle |
| `download` | Transferir | Baixar |
| `register` | Registar | Criar conta |
| `login` | Iniciar sessão | Entrar |
| `logout` | Terminar sessão | Sair |

The same applies to compliance wording: `pt` follows GDPR terminology
("Encarregado de Proteção de Dados"), `pt-BR` follows LGPD ("encarregado pelo
tratamento de dados pessoais").

## Semantic keys

`resources/lang/catalog.json` holds a larger catalog with dotted, semantic keys
across all four locales:

```json
{
  "en":    { "auth.login.failed": "We couldn't sign you in." },
  "pt-BR": { "auth.login.failed": "Não foi possível entrar." }
}
```

Semantic keys survive copy changes: `auth.login.failed` still makes sense when
the wording changes, where a key named after the text does not.

The catalog is not wired into the seeder — the shipped views still use flat keys
(`__('login')`). Adopting it is a migration, not an addition.

## Placeholders

Keep interpolation in the catalog rather than concatenating strings:

```python
__("welcome_{name}", "pt-BR", name="Ana")     # "Olá, Ana!"
```

Placeholders must match across locales — a key with `{min}` in English needs
`{min}` everywhere, or the value is dropped in that language.

## Adding a locale

1. Add its entries to `TRANSLATIONS` in the seeder.
2. Re-seed: `python craft.py db seed`.
3. Set `APP_LOCALE`, or pass the locale per call.

Only the keys that differ from the base language are needed — the chain covers
the rest.
