# Contributing to Codepy

Thanks for considering a contribution. This document covers how to get set up,
what the project expects from a change, and how to report problems.

## Getting set up

```bash
git clone <your-fork-url> codepy
cd codepy
pip install -e ".[dev]"

cp .env.example .env
python craft.py key:generate
python craft.py migrate --seed
python -m pytest
```

Docker gets you the same environment plus PostgreSQL:

```bash
docker compose up -d --build
docker exec framework python -m pytest
```

## Running the test suite

The suite must pass on **all three** targets before a pull request is ready.
Dialect bugs and version bugs only show up on the target that exercises them.

```bash
# SQLite in memory (the default)
python -m pytest

# PostgreSQL
docker exec framework-db psql -U codepy -d codepy_db -p 5499 -c "CREATE DATABASE codepy_validation;"
CODEPY_TEST_DB=pgsql DB_HOST=127.0.0.1 DB_PORT=5499 \
  DB_DATABASE=codepy_validation DB_USERNAME=codepy DB_PASSWORD=secretpassword \
  python -m pytest

# Python 3.11, the minimum supported version
docker exec framework python -m pytest
```

Every test file must also pass **on its own**:

```bash
python -m pytest tests/test_orm_model.py
```

A file that only passes as part of the full run is relying on state another test
left behind. That has bitten this project more than once.

## What a good change looks like

**Source code is English.** Identifiers, comments, docstrings, commit messages.
User-facing strings go through the translation layer instead.

**Behaviour changes come with tests.** Not tests that assert the implementation,
tests that would fail if the behaviour regressed. For example, the eager-loading
tests count the SQL queries issued — asserting only on results would pass just as
happily with the N+1 bug they exist to prevent.

**Never degrade silently.** The single largest source of bugs found in this
codebase was code that swallowed an error and returned something plausible: a
view engine returning a placeholder instead of raising, a queue building a fake
payload, a form request returning input it never validated. All of them had
green tests. If a failure cannot be handled, let it raise or log it — do not
paper over it with `except Exception: pass`.

**Keep the diff to the change.** Reformatting unrelated code makes review harder.

## Adding a translation

Locales follow BCP 47: lowercase language, uppercase region — `en`, `pt`,
`pt-BR`, `es`. Lookups fall back `pt-BR → pt → en`, so a regional locale only
needs the keys where it genuinely differs from its base language.

Add entries to `database/seeders/TranslationSeeder.py`. The richer,
semantically-keyed catalog lives in `resources/lang/catalog.json`.

## Building a release

```bash
python -m pip install build twine
python -m build              # writes dist/*.whl and dist/*.tar.gz
python -m twine check dist/*
```

Building requires **setuptools 77+** — the project uses PEP 639 metadata
(`license` as an SPDX string plus `license-files`), which older versions reject.

Verify the artifact by installing it somewhere the source tree is not
importable, or you end up testing `services/` on disk rather than the wheel:

```bash
unset PYTHONPATH            # a venv does not override it
python -m venv /tmp/clean
cd /tmp
/tmp/clean/bin/pip install /path/to/dist/codepy-0.1.0-py3-none-any.whl
/tmp/clean/bin/python -c 'import services; print(services.__file__)'
/tmp/clean/bin/craft --help
```

`services.__file__` must point inside `site-packages`. If it points at your
checkout, the test proved nothing.

## Reporting a bug

This project is developed locally and is not published. Report problems to
**snarthost@gmail.com** with:

- what you expected and what happened instead
- the database driver and Python version
- the smallest snippet that reproduces it

For security issues, see [SECURITY.md](SECURITY.md).

## Landing a change

1. Branch from `master`.
2. Make the change, with tests.
3. Run the suite on all three targets.
4. Update `CHANGELOG.md` under "Não lançado".
5. Merge, with a commit message describing what changed and why.

## Licence

By contributing you agree that your work is licensed under the
[MIT License](LICENSE) that covers this project.
