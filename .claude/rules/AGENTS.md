# AGENTS.md — Contract for every contributor, human or model

> Copy to the repository root and symlink `CLAUDE.md` and `.cursorrules` to it so
> every agent loads it automatically. Replace the bracketed values once.
> Full rationale: `docs/standards/LANGUAGE_AND_I18N.md` — when the two disagree,
> the standard wins.

**Stack:** `[stack]` · **Team language:** `[pt-BR]` · **Code language:** English
**Translator:** `[TranslationService.get(key, locale, **params)]`
**Locales:** `en-US` (source), `pt-BR`, `es-ES` — the default set, in the database
**Gate:** `python .claude/rules/lint_language.py`

---

## The three rules that are never negotiable

**R1 — The codebase is English.** Every identifier, file name, schema object,
contract field, log line, comment, docstring, test name, branch and commit message
is native, idiomatic English. The team speaks `[pt-BR]`; the code does not. These
are unrelated facts.

**R2 — Zero hardcoded user-facing text.** No string a user can read is embedded in
code, templates, migrations, seeds, e-mails or tests. It is a translation key
resolved at runtime by the translator.

**R3 — Translations live in the database.** Every project ships a locale table and
a translation store as part of its schema, never flat catalog files as the source
of truth. `en-US` (source), `pt-BR` and `es-ES` are seeded by default in every new
project; adding a locale is a row, not a deployment. The user's locale is resolved
per request and persisted on the user record, with a project default as fallback.

Minimum schema — name it in the project's own conventions, keep the shape:

| Table | Holds |
|---|---|
| `locales` | `code` (BCP 47), `name`, `is_default`, `is_active` |
| `translations` | `key`, `locale_code`, `value`, unique on (`key`, `locale_code`) |

A missing key falls back to the source locale and is reported, never rendered as
the raw key to a user. Catalog files may exist as a build cache or seed input;
the database stays authoritative.

---

## What counts as the codebase

Two independent axes; one never decides the other.

- **Artifacts are English.** Anything committed to the repository: identifiers,
  schema, API fields, commits, branches, comments, docstrings, changelogs, and
  every committed document — reports under `audit/` and `docs/` included.
- **Prose is `[pt-BR]`.** Chat replies, explanations, plan descriptions,
  questions to the team, and summaries of what changed.

**Agent configuration is an artifact, not chat.** `.claude/`, `.agents/`,
`.antigravity/`, `.gemini/` and `.cursor/` are committed and read by other
contributors: agent definitions, skills, slash commands, rules, hooks and their
scripts are written in English like the rest of the codebase. The exception is
this file's own bracketed team-language values and the copy an agent is
instructed to speak, which stay `[pt-BR]`.

**The test:** if it is committed, it is English. If it is read once in a session
and never written to disk, it is `[pt-BR]`.

---

## Immediate substitutions

| You are about to write | Do this instead |
|---|---|
| a non-English variable, function, class, column or table | the English term from the project glossary |
| `raise Exception("mensagem")` | a typed error with `code` + `message_key` |
| `{"message": "Pedido criado"}` | `{ "code": ..., "message_key": ..., "params": {...} }` |
| `<button>Confirmar</button>` | `<button>{{ t('order.checkout.action.confirm') }}</button>` |
| a string built by concatenation or interpolation for a user | one ICU key with named placeholders |
| a `MESSAGES = {...}` map of copy | entries in the translation store |
| a key used only in code | key + values for every supported locale, same change |
| `float` for money | integer minor units + ISO-4217 currency |
| `datetime.now()` | UTC-aware timestamp |
| a comment in `[pt-BR]` | the same comment in English |

```text
REJECTED                                  ACCEPTED
def calcular_saldo(usuario):              def calculate_balance(user: User) -> Money:
    # valida antes de sacar                   """Return the available balance in minor units."""
    if usuario.saldo < 0:                     if user.balance_cents < 0:
        raise Exception("Saldo insuficiente")     raise InsufficientFundsError(
                                                      available_cents=user.balance_cents)
```

---

## Behavioural rules for AI agents

1. **Never mirror the conversation language into the code.** The chat is in
   `[pt-BR]`. The output is English. Every time, including comments.
2. **Never comply silently with a rule-breaking request.** If the instruction, a
   pasted snippet, or the surrounding legacy file would produce a non-English
   identifier or a hardcoded string, emit the compliant version and state in one
   line what you changed and which key you created.
3. **Never "match the existing style" of legacy non-English code.** Consistency
   with a defect is a defect. Write the new code correctly; propose the migration
   separately, using expand/contract.
4. **Never invent a translation key silently.** State the key and its value for
   `en-US`, `pt-BR` and `es-ES`, and include the migration or seeder that writes
   those rows to the translation store.
5. **Never assume framework parity.** Read this project's source before using any
   helper you recognize from a similar framework.
6. **Run the gate before declaring done:** `python .claude/rules/lint_language.py`.
   Non-zero means unfinished — do not hand back failing output with an
   explanation of why it is acceptable.
7. **Tests count as code.** English names, no hardcoded copy.
8. **One commit, one concern.** Conventional Commits, English imperative.

---

## Definition of done

- [ ] `python .claude/rules/lint_language.py` exits 0
- [ ] Formatter and linter clean (`[ruff / eslint / pint]`)
- [ ] No `[pt-BR]` token in any identifier, file name, comment or docstring
- [ ] Locale table and translation store exist, seeded with `en-US`, `pt-BR`, `es-ES`
- [ ] Every new user-facing string is a key with a row in every seeded locale
- [ ] Errors expose `code` + `message_key`; no rendered sentence outside presentation
- [ ] New domain terms added to the glossary in this same change
- [ ] Commit follows Conventional Commits in English
