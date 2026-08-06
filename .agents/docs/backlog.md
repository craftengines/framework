# Backlog — Codepy Framework (base para novas aplicações)

> Contexto: este repositório é o **framework base** usado para criar novas aplicações
> (equivalente ao `laravel/laravel`), não uma aplicação de negócio.
> Estado da suíte: **265/265 passando** em SQLite (`:memory:`), em PostgreSQL real e
> no Python 3.11 do container. Cada arquivo de teste também passa isolado — nenhum
> depende da ordem de execução.

## Como rodar

```powershell
# SQLite (padrão)
python -m pytest -q

# PostgreSQL real (container framework-db, porta 5499)
docker exec framework-db psql -U codepy -d codepy_db -p 5499 -c "CREATE DATABASE codepy_validation;"
$env:CODEPY_TEST_DB="pgsql"; $env:DB_HOST="127.0.0.1"; $env:DB_PORT="5499"
$env:DB_DATABASE="codepy_validation"; $env:DB_USERNAME="codepy"; $env:DB_PASSWORD="secretpassword"
python -m pytest -q

# CLI
python craft.py migrate | migrate:status | migrate:rollback | db seed | route list | make model X -m

# Docker (app em http://localhost:8300)
docker compose up -d --build
docker exec framework python -m pytest -q   # valida no Python 3.11, o mínimo suportado
```

---

## ✅ Concluído

### Bloqueadores corrigidos
- **Pacote não importava.** O core estava em `framework/` mas os 83 imports internos
  diziam `services.*`. Diretório renomeado de volta para `services/`.
- **`import codepy` resolvia para um pacote CUDA de terceiros** do site-packages.
  Substituído por um `MetaPathFinder` em `services/__init__.py` que mapeia
  `codepy.* → services.*` (a lista manual de ~40 aliases foi removida).
- **`.env` nunca era lido** — `env()` só via variáveis reais do SO. Loader criado com
  interpolação `${VAR}`, chamado em `Application.register_config()`.

### Subsistemas que eram arquivos vazios (0 linhas)
| Arquivo | Entregue |
|---|---|
| `services/orm/connection.py` (novo) | Drivers SQLite/PostgreSQL/MySQL, tradução `?`/`:nome` → `%s`, `Row` com acesso por atributo/chave/índice, transações, `search_path` |
| `services/migrations/schema.py` | `Blueprint` fluente + `Grammar` por dialeto, FKs, índices compostos, estilos fluente e kwargs |
| `services/migrations/migrator.py` | Descoberta, tabela `migrations`, batches, `run/rollback/reset/refresh/fresh/status`, `--step`, `--pretend` |
| `services/cli/app.py` + `generators.py` | `craft`: `migrate:*`, `db seed/show/tables/ping/wipe`, 12 geradores `make:*`, `route list`, `queue work`, `serve`, `tinker`, `key:generate` |
| `services/cache/manager.py` | Stores array/file/redis com TTL, `remember`, `increment`, degradação para array se o Redis cair |
| `services/auth/password.py` | `Hash` com bcrypt (passlib) e fallback PBKDF2-SHA256 |
| `services/auth/manager.py` | `attempt/validate/once/login/login_using_id/logout`, comparação de tempo constante para usuário inexistente |
| `services/orm/relationships.py` | `HasOne/HasMany/BelongsTo/BelongsToMany` com `attach/detach/sync`, proxy para o QueryBuilder, **eager loading** (`with_()`) |
| `services/orm/soft_deletes.py` | `delete/restore/force_delete/trashed`, escopos `with_trashed/only_trashed` |
| `services/seeding/`, `services/factories/` | `Seeder.call()`, `Factory.state/make/create` |
| `services/exceptions/handler.py` | `ExceptionHandler` real (JSON/HTML, trace só com `app.debug`) |

### Bugs reais corrigidos
- `Model.create` usava `SELECT last_insert_rowid()` — quebra em Postgres. Agora
  `insert_get_id()` com `RETURNING id` no Postgres.
- `Model.permissions()`: JOIN em `pr.role_id` em vez de `pr.permission_id`. Passava
  por acaso porque os ids eram 1.
- `QueueManager` era **falso**: montava um payload com as chaves `"TestJob"` e `"999"`
  hardcoded para o teste passar. Reescrito com serialização JSON real, retry/backoff
  e `available_at`.
- Migration `framework_dynamic_tables`: `role_user` usava `uuid` para `user_id`
  (users.id é auto-increment) e `permission_role` era dropada no `down()` mas nunca
  criada no `up()`.
- Migration `jobs`: `available_at`/`created_at` como INTEGER recebendo string ISO.
- `GateManager.allows()` retornava `True` para qualquer ability desconhecida —
  **falha aberta**. Agora nega por padrão e resolve policies.
- `Container.__init__` fazia `Container._instance = self` incondicionalmente:
  construir uma segunda `Application` (teste, worker, escopo de tenant) sequestrava
  o singleton do processo inteiro e repontava os 16 `Container.getInstance()` do
  framework. Agora construir não reivindica; `Application` só assume se ninguém
  assumiu (`bind_as_global` força ou proíbe), e `Container.scoped_instance()` troca
  temporariamente com restauração garantida.
- Senha era gravada em texto puro pelo seeder. `User.create` agora hasheia.
- `datetime.utcnow()` deprecado no Python 3.12+.
- `services/security/captcha.py` usava `Any` sem importar. Passava no Python 3.14
  (anotações lazy, PEP 649) e quebrava no 3.11 — que é o mínimo do `pyproject` e a
  versão do container. O `validate()` também tinha `and code != "WRONG"` hardcoded
  para o teste passar; agora usa `secrets.compare_digest` e limpa o código sempre
  (single-use, senão dá para brutar contra um mesmo desafio).
- `FacadeMeta.__getattr__` fabricava **qualquer** atributo, inclusive dunders. A
  coleta do pytest (e `inspect`/`copy`/`pickle`) sonda nomes como `__wrapped__` e
  `__test__` em objetos de módulo; isso resolvia o container antes do boot, e o
  `getInstance()` criava um `Container` vazio que reivindicava o global — daí as
  bindings da aplicação real nunca apareciam. Agora nomes com `_` levantam
  `AttributeError`, e um container de fallback é sempre deslocado pela `Application`.
  Sintoma: arquivos de teste que importavam uma facade no topo sem importar
  `bootstrap.app` só passavam se outro arquivo tivesse booted o app antes.
- Docker: o container montava `D:\data\www\codepy` — o nome da pasta **antes** de
  virar "codepy framework". `/app` subia vazio e o app ficava em loop de restart.
- `Dockerfile` tinha `COPY src/ ./src/` (pasta inexistente, build falhava) e um CMD
  com comandos que não existem na CLI (`key-generate`, `migrate-fresh`, `db:seed`).

### Limpeza
- Removido o domínio SoftPax (funerária/cemitério): 16 migrations, 18 models,
  26 controllers, 3 pastas de views. Backup em
  `%TEMP%/claude/.../scratchpad/backup-pre-cleanup.zip`.
- `craft.py` da raiz apontava para `src.routes.web`, módulo inexistente.
- `pyproject.toml`: entrypoint `codepy.cli.app:cli` → `craft = services.cli.app:main`.
- Containers renomeados: `framework` (app) e `framework-db`; prod virou
  `framework-prod-app` / `framework-prod-db`. Projeto Compose fixado em
  `name: framework` (o diretório tem espaço no nome). O banco de dev ganhou volume
  nomeado — antes ficava na camada do container e sumia a cada recriação.

### Testes criados (250 novos)
`test_schema_grammar.py`, `test_connection.py`, `test_migrator.py`,
`test_query_builder.py`, `test_auth.py`, `test_cache.py`,
`test_cli_generators.py`, `test_orm_model.py`, `test_container.py`,
`test_eager_loading.py`, `test_facades.py`.
`conftest.py` roda as migrations reais e aceita `CODEPY_TEST_DB=pgsql`.

`test_eager_loading.py` **conta as queries emitidas** em vez de só conferir
resultados — asserção sobre resultado passaria igual com lazy loading, que é
exatamente o bug que se quer impedir.

---

## 🔜 Próximas fatias

### 1. Eager loading aninhado e sob demanda
`with_()` cobre um nível. Faltam `with_("posts.comments")` (aninhado) e
`Collection.load("posts")` (carregar depois da query). Também não há
`with_count()`.

### 2. Sessão, CSRF e guard de API
- `AuthManager` guarda o usuário em memória de instância — não sobrevive entre
  requests. Falta backend de sessão.
- Não há middleware CSRF (o `FrameworkSeeder` anuncia "validações CSRF" que não existem).
- Guard `api` está configurado em `config/auth.py` mas não implementado.
- `TenantMiddleware` chama `Auth.user()`, que sempre retorna `None` sem sessão.

### 3. Camada HTTP
- `services/http/kernel.py` e `router.py` não têm testes.
- `Validator` cobre só `required/string/integer` — faltam `email`, `min`, `max`,
  `confirmed`, `unique`, `exists`.
- `Resource`/`Controller` são casca fina; sem testes.

### 4. Arquivos ainda vazios
`services/coreengine/engine.py`, `services/orm/collection.py` (duplica
`services/support/collection.py` — decidir qual fica), `services/resources/base.py`,
`services/exceptions/base.py`, `services/support/helpers.py`,
`services/view/__init__.py`, `app/Models/__init__.py`.

### 5. Higiene de repositório
- **Não é um repositório git.** `git init` — hoje qualquer erro é irreversível.
  E `.github/workflows/deploy.yml` já roda a suíte em Python 3.11 (a versão certa):
  o bug do `captcha.py` teria sido pego na hora. O CI nunca rodou porque não há repo.
- `index.html` (33 KB) e `package.json` na raiz parecem sobra de landing page.
- `scratch/` e `.pytest_cache/` versionados.
- `.agents/.agents/` e `.ai/.agents/` são aninhamentos duplicados.
- passlib + bcrypt 4.x é incompatível neste ambiente (`module 'bcrypt' has no
  attribute '__about__'`); o framework detecta e cai no PBKDF2. Fixar `bcrypt<4.1`
  ou migrar para `argon2-cffi` resolve de vez.

### 6. Documentação
`README.md` e `CODEPY_DESIGN.md` (74 KB) descrevem o estado anterior: citam
`services/orm` com SQLAlchemy pooling (não é o caso — é DB-API direto) e o layout
antigo. Atualizar depois que a API estabilizar.
