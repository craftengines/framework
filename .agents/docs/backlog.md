# Backlog — Craft Framework (base para novas aplicações)

> Contexto: este repositório é o **framework base** usado para criar novas aplicações
> (o esqueleto que se copia para iniciar uma app), não uma aplicação de negócio.
>
> Estado: **503/503 testes passando** em SQLite, PostgreSQL real e Python 3.11 do
> container. Cada arquivo de teste também passa isolado — nenhum depende da ordem.
> App real validado em `http://localhost:8300`, incluindo o fluxo de login com
> CSRF e captcha.

## Como rodar

```powershell
# SQLite (padrão)
python -m pytest -q

# PostgreSQL real (container framework-db, porta 5499)
docker exec framework-db psql -U craft -d craft_db -p 5499 -c "CREATE DATABASE craft_validation;"
$env:CRAFT_TEST_DB="pgsql"; $env:DB_HOST="127.0.0.1"; $env:DB_PORT="5499"
$env:DB_DATABASE="craft_validation"; $env:DB_USERNAME="craft"; $env:DB_PASSWORD="secretpassword"
python -m pytest -q

# Docker (app em http://localhost:8300)
docker compose up -d --build
docker exec framework python -m pytest -q   # valida no Python 3.11, o mínimo suportado

# CLI
python dev.py migrate | migrate:status | migrate:rollback | db seed | route list | make model X -m
```

---

## ✅ Concluído

### Bloqueadores corrigidos

- **Pacote não importava.** O core estava em `framework/` mas os 83 imports internos
  diziam `services.*`. Diretório renomeado de volta para `services/`.
- **`import craft` resolvia para um pacote CUDA de terceiros** do site-packages.
  Substituído por um `MetaPathFinder` em `services/__init__.py` que mapeia
  `craft.* → services.*` (a lista manual de ~40 aliases foi removida).
- **`.env` nunca era lido** — `env()` só via variáveis reais do SO. Loader criado com
  interpolação `${VAR}`, chamado em `Application.register_config()`.

### Subsistemas que eram arquivos vazios (0 linhas)

| Arquivo | Entregue |
|---|---|
| `services/orm/connection.py` (novo) | Drivers SQLite/PostgreSQL/MySQL, tradução `?`/`:nome` → `%s`, `Row` com acesso por atributo/chave/índice, transações, `search_path` |
| `services/migrations/schema.py` | `Blueprint` fluente + `Grammar` por dialeto, FKs, índices compostos, estilos fluente e kwargs |
| `services/migrations/migrator.py` | Descoberta, tabela `migrations`, batches, `run/rollback/reset/refresh/fresh/status`, `--step`, `--pretend` |
| `services/cli/app.py` + `generators.py` | `dev`: `migrate:*`, `db seed/show/tables/ping/wipe`, 12 geradores `make:*`, `route list`, `queue work`, `serve`, `tinker`, `key:generate` |
| `services/cache/manager.py` | Stores array/file/redis com TTL, `remember`, `increment`, degradação para array se o Redis cair |
| `services/auth/password.py` | `Hash` com bcrypt (passlib) e fallback PBKDF2-SHA256 |
| `services/auth/manager.py` | `attempt/validate/once/login/logout`, sessão persistente, comparação de tempo constante |
| `services/orm/relationships.py` | `HasOne/HasMany/BelongsTo/BelongsToMany`, `attach/detach/sync`, **eager loading** |
| `services/orm/soft_deletes.py` | `delete/restore/force_delete/trashed`, `with_trashed/only_trashed` |
| `services/http/session.py` (novo) | Sessão com drivers cookie e file, assinatura HMAC, flash data, token CSRF |
| `services/seeding/`, `services/factories/` | `Seeder.call()`, `Factory.state/make/create` |
| `services/exceptions/handler.py` | `ExceptionHandler` real (JSON/HTML, trace só com debug, 5xx vs 4xx) |

### Camada HTTP construída

- **Sessão** (`StartSession`) — drivers cookie e file, ambos assinados com `APP_KEY`.
  Cookie adulterado ou assinado com outra chave é rejeitado.
- **CSRF** (`VerifyCsrfToken`) — POST/PUT/PATCH/DELETE via `_token` ou header
  `X-CSRF-TOKEN`, rotas `api/*` isentas, falha devolve 419.
- **Autenticação** (`Authenticate`) — reidrata o usuário da sessão a cada request.
  O login rotaciona o id da sessão (fecha session fixation).
- **Guard de API** (`AuthenticateApiToken`) — `Authorization: Bearer`.
- **Request** — corpo parseado antes do pipeline, então controllers síncronos leem
  `input()`, `only()`, `boolean()`, `file()`, `session()`, `user()`, `bearer_token()`.
  O monkeypatch em `StarletteRequest` foi removido.
- **Validator** — de 3 regras para ~30: presença, tipos, formatos, tamanho,
  conjuntos e banco (`unique`, `exists`).

### Bugs reais corrigidos

- `Model.create` usava `SELECT last_insert_rowid()` — quebra em Postgres. Agora
  `insert_get_id()` com `RETURNING id`.
- `Model.permissions()`: JOIN em `pr.role_id` em vez de `pr.permission_id`. Passava
  por acaso porque os ids eram 1.
- `QueueManager` era **falso**: payload com as chaves `"TestJob"` e `"999"` hardcoded
  para o teste passar. Reescrito com serialização JSON real, retry/backoff.
- `Captcha.validate` tinha `and code != "WRONG"` hardcoded, mesmo padrão. Agora usa
  `secrets.compare_digest` e limpa o código sempre (single-use).
- `FormRequest.validated()` **não validava nada** — devolvia o corpo cru, ignorando
  `rules()` e `authorize()`. Toda regra declarada era silenciosamente ignorada.
- **O motor de views nunca renderizou um layout.** O Forge não implementava nenhuma`n  das diretivas (apesar da docstring e da documentação prometerem `@csrf`/`@auth`)
  e engolia toda exceção devolvendo `<div>Rendered view: x</div>`. Como
  `@extends("layouts.app")` entregava a notação de ponto crua ao Jinja, as 12 views
  que estendem um layout falhavam em silêncio, com HTTP 200. O `Controller.view()`
  tinha o mesmo fallback, mascarando o erro por baixo.
- `documentation/security.md` afirmava que os cookies de sessão eram assinados com
  criptografia **pós-quântica** e que "não podem ser lidos". Os dois falsos: a
  assinatura é HMAC-SHA256, e no driver de cookie o payload é JSON legível pelo
  cliente (assinado, não criptografado). Corrigido com aviso explícito.
- **`Resource` vazava o modelo inteiro.** A classe base lia
  `self.resource.to_dict()`, então uma subclasse que definisse `to_dict()` — que é
  exatamente o que `craft make:resource` gerava — era ignorada e o modelo saía
  completo, incluindo campos que o dev escolheu não expor. É o oposto da função de
  um API Resource. O gerador também foi corrigido para emitir `to_array()`.
- `EventDispatcher.listen(Evento, UmListener)` levantava `'type' object is not
  iterable` — exigia lista. E listeners registrados numa classe base **não ouviam
  suas subclasses**, então um listener genérico nunca disparava para os eventos
  concretos que de fato são despachados.
- `ModuleManager.enable()/disable()` retornavam `True` incondicionalmente: um erro
  de digitação no slug parecia sucesso.
- `PluginManager.trigger_hook()` engolia exceção de plugin sem registrar nada — um
  plugin que quebrava a cada chamada era invisível. A falha continua isolada (um
  plugin ruim não derruba o request), mas agora é logada.
- `GateManager.allows()` retornava `True` para qualquer ability desconhecida —
  **falha aberta**. Agora nega por padrão e resolve policies.
- **Middleware por rota era decorativo**: `.middleware("auth")` era ignorado pelo
  kernel. Agora resolve por alias, e um alias desconhecido levanta erro no boot.
- **Middleware era instanciado a cada request** — o store de sessão e sua chave de
  assinatura eram recriados toda vez, então nenhum cookie sobrevivia.
- `FacadeMeta.__getattr__` fabricava qualquer atributo, inclusive dunders. A coleta
  do pytest sondava `__wrapped__`/`__test__`, o que resolvia o container antes do
  boot e fazia um `Container` vazio reivindicar o global.
- `Container.__init__` reivindicava o singleton global incondicionalmente: uma
  segunda `Application` sequestrava o processo inteiro.
- `Starlette(debug=True)` fixo no kernel — vazaria stack traces em produção.
- 4xx eram logados com traceback completo, enterrando as falhas reais.
- `services/security/captcha.py` usava `Any` sem importar: passava no Python 3.14
  (anotações lazy, PEP 649) e quebrava no 3.11, o mínimo declarado.
- Migration `framework_dynamic_tables`: `role_user` usava `uuid` para `user_id` e
  `permission_role` era dropada no `down()` mas nunca criada no `up()`.
- Migration `jobs`: `available_at`/`created_at` como INTEGER recebendo string ISO.
- Senha era gravada em texto puro pelo seeder. `User.create` agora hasheia.
- Docker: o container montava `D:\data\www\craft`, o nome da pasta antes de virar
  "craft framework". `/app` subia vazio e o app ficava em loop de restart.
- `Dockerfile` tinha `COPY src/` (pasta inexistente) e um CMD com comandos que não
  existem na CLI (`key-generate`, `migrate-fresh`, `db:seed`).

### Limpeza

- Removido o domínio SoftPax (funerária/cemitério): 16 migrations, 18 models,
  26 controllers, 3 pastas de views.
- Removidos arquivos mortos: `app/main.py` (FastAPI paralelo), `home_controller.py`,
  `BaseModel.py` (models SQLAlchemy do SoftPax), `coreengine/`, e 4 arquivos vazios
  sem nenhuma referência.
- Removida a landing page `craft-showcase` (vite) da raiz do esqueleto.
- Dependências enxugadas: saíram `sqlalchemy`, `alembic`, `pydantic`,
  `pydantic-settings` e `click` — nenhuma era usada, e o `alembic` competia
  conceitualmente com o migrator próprio. `pytest`/`httpx` viraram extra `[dev]`.
- `bcrypt` fixado em `<4.1`: acima disso o passlib quebra (`__about__` removido).
- Containers renomeados: `framework` e `framework-db`; prod virou
  `framework-prod-app`/`framework-prod-db`. Projeto Compose fixado em
  `name: framework` (o diretório tem espaço no nome).
- Banco de dev ganhou volume nomeado — antes ficava na camada do container.
- **`git init` feito**: o repositório agora é versionado.

### Testes (410, de 15 no início)

`test_schema_grammar`, `test_connection`, `test_migrator`, `test_query_builder`,
`test_auth`, `test_cache`, `test_cli_generators`, `test_orm_model`,
`test_container`, `test_eager_loading`, `test_facades`, `test_session`,
`test_http_middleware`, `test_validation`, `test_form_request`,
`test_exception_handler`.

Três pontos de método que valem manter:

- `test_eager_loading` **conta as queries emitidas**. Asserção só sobre resultado
  passaria igual com lazy loading, que é exatamente o bug a impedir.
- `conftest.py` constrói o schema com o **migrator real**, então as migrations são
  exercitadas a cada rodada em vez de dependerem de fixtures paralelas.
- `test_subsystems_persistence` **lê as tabelas de volta**. Settings e Modules caem
  para memória quando a query falha, então o teste antigo passava inteiramente pelo
  caminho em memória e a persistência nunca era exercitada.

### O padrão que rendeu a maioria dos bugs

Seis bugs desta sessão vieram do mesmo lugar: **código que degrada em silêncio
para algo plausível**. A fila com payload hardcoded, o captcha com `!= "WRONG"`, o
`FormRequest` que devolvia o corpo cru, o Forge com `<div>Rendered view: x</div>`,
o `Resource` que caía para o modelo inteiro, o `ModuleManager` que sempre retornava
`True`. Todos tinham teste verde. O sinal a desconfiar não é o teste vermelho — é o
`except Exception: pass` e o fallback que devolve algo com cara de certo.

Varredura feita: os 23 `except: pass` restantes em `services/` e `app/` foram
revisados um a um. Os que sobraram são legítimos — fallback de dependência
opcional (redis, bcrypt), cleanup best-effort ao fechar conexão, e degradação
deliberada quando não há banco. Nenhum esconde erro do usuário.

---

## 🔜 Próximas fatias

### 1. Eager loading aninhado e sob demanda

`with_()` cobre um nível. Faltam `with_("posts.comments")` (aninhado),
`Collection.load("posts")` (carregar depois da query) e `with_count()`.

### 2. Remember-me e reset de senha

`attempt()` não tem `remember` (removido em vez de fingir que funcionava) e não há
fluxo de recuperação de senha nem verificação de e-mail.

### 3. Camada HTTP restante

- `services/http/router.py` e `kernel.py` ainda sem testes diretos (são exercitados
  indiretamente por `test_http_middleware`, `test_view` e `test_framework`).
- `Resource` é casca fina; sem testes.
- Sem rate limiting.
- Sem `_old_input`: o helper `old()` da view existe, mas nada popula a sessão com
  os dados do formulário após uma validação falhar.

### 3b. Criptografia de sessão

O driver `cookie` assina mas **não criptografa** — o payload é legível pelo
cliente. Frameworks maduros costumam criptografar. Hoje a orientação é usar `SESSION_DRIVER=file`
para dados sensíveis; adicionar cifra ao driver de cookie fecharia a lacuna.

### 4. Filas

Driver `database` e `sync` existem; falta Redis, `failed_jobs` persistida e worker
com múltiplos processos.

### 5. Decisão pendente: FastAPI

O framework é construído **diretamente sobre Starlette** — `fastapi` está nas
dependências e no nome do projeto, mas não é importado em lugar nenhum. Manter por
identidade ou remover por honestidade é uma decisão sua.

### 6. Documentação

`CRAFT_DESIGN.md` (74 KB) ainda descreve o desenho antigo. O `README.md` e
`documentation/*.md` foram atualizados.
