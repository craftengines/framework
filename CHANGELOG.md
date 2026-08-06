# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento por [Semantic Versioning](https://semver.org/lang/pt-BR/).

O projeto está em `0.x`: a API pública ainda pode mudar entre versões menores.

---

## [Não lançado]

Trabalho de validação do esqueleto base, de "não importa" até 530 testes verdes
em SQLite, PostgreSQL real e Python 3.11.

### Adicionado

**Banco de dados**

- Camada de conexão multi-driver (`services/orm/connection.py`): SQLite,
  PostgreSQL e MySQL com o mesmo SQL. Placeholders `?` e `:nome` são traduzidos
  para o paramstyle de cada driver.
- Split de leitura/escrita e schema-por-tenant no PostgreSQL
  (`set_tenant_schema`, `ensure_tenant_schema`).
- Migrator com batches, `run/rollback/reset/refresh/fresh/status`, `--step` e
  `--pretend`.
- Schema builder com `Blueprint` fluente e DDL por dialeto, chaves estrangeiras
  e índices compostos. Estilos fluente e keyword são intercambiáveis:
  `t.string("cpf").nullable()` == `t.string("cpf", nullable=True)`.

**CLI `craft`**

- `migrate:*`, `db seed/show/tables/ping/wipe`, `route list`, `queue work`,
  `serve`, `tinker`, `key:generate` e 12 geradores `make:*`.
- Aceita `migrate:status` e `migrate status`.

**HTTP**

- Sessão com drivers `cookie` e `file`, ambos assinados com HMAC-SHA256 usando
  `APP_KEY`. Flash data e token CSRF inclusos.
- Middleware `StartSession`, `VerifyCsrfToken`, `Authenticate`, `RequireAuth` e
  `AuthenticateApiToken`.
- Middleware por rota resolvido por alias (`auth`, `api`, `session`, `csrf`).
- `Request` com o corpo parseado antes do pipeline: `input()`, `only()`,
  `boolean()`, `file()`, `session()`, `user()`, `bearer_token()`.
- Motor de views Forge com diretivas Blade (`@csrf`, `@auth`, `@guest`, `@can`,
  `@if`, `@foreach`, `@extends`, `@section`, `@yield`, `@include`, `@method`) e
  helpers globais (`csrf_field`, `auth`, `config`, `route`, `session`, `__`).

**ORM**

- Eager loading via `with_()`: uma query por relação em vez de N+1.
- `HasOne`, `HasMany`, `BelongsTo` e `BelongsToMany` com `attach/detach/sync`.
- Soft deletes com `with_trashed()` / `only_trashed()` / `restore()`.
- Query builder com `or_where`, `where_in`, `where_null`, `where_between`,
  `join`, `group_by`, `having`, `paginate` e agregações.

**Autenticação e validação**

- `Hash` com bcrypt e fallback PBKDF2-SHA256.
- `AuthManager` com sessão persistente; o login rotaciona o id da sessão.
- Validator de 3 para ~30 regras, incluindo `unique` e `exists`.

**i18n**

- Locales BCP 47 com cadeia de fallback `pt-BR → pt → en`.
- `normalize_locale` canonicaliza `PT-br` → `pt-BR` e `EN` → `en`.
- Quatro locales seedados: `en`, `pt` (europeu), `pt-BR`, `es`.
- Placeholders: `__("welcome_{name}", "pt-BR", name="Ana")`.
- `resources/lang/catalog.json` com 75 chaves semânticas × 4 locales, incluindo
  textos de consentimento alinhados a LGPD/GDPR (opt-in, essenciais isentos de
  consentimento, revogação explícita).

**Outros**

- Cache com stores array/file/redis, TTL, `remember` e `increment`.
- Fila com serialização JSON, retry com backoff e `available_at`.
- Seeders e factories.
- Carregamento de `.env` com interpolação `${VAR}`.
- Suíte de 530 testes (eram 15).

### Corrigido

**Bloqueadores**

- O pacote não importava: o core estava em `framework/` enquanto os 83 imports
  internos diziam `services.*`.
- `import codepy` resolvia para um pacote CUDA de terceiros do site-packages.
  Substituído por um `MetaPathFinder` que mapeia `codepy.* → services.*`.
- `.env` nunca era lido — `env()` só via variáveis reais do SO.

**Segurança**

- `Gate.allows()` retornava `True` para qualquer permissão desconhecida —
  falha aberta. Agora nega por padrão.
- Middleware por rota era ignorado pelo kernel: `.middleware("auth")` era
  proteção decorativa.
- Senha era gravada em texto puro pelo seeder.
- `Starlette(debug=True)` fixo no kernel vazaria stack traces em produção.
- `Resource` vazava o modelo inteiro: a classe base lia
  `self.resource.to_dict()`, então uma subclasse que definisse `to_dict()` — o
  que o gerador emitia — era ignorada e campos não expostos saíam na resposta.

**Comportamento**

- `Model.create` usava `SELECT last_insert_rowid()`, que quebra em PostgreSQL.
- JOIN incorreto em `Model.permissions()` (`pr.role_id` em vez de
  `pr.permission_id`).
- `FormRequest.validated()` devolvia o corpo cru sem validar nada, ignorando
  `rules()` e `authorize()`.
- O motor de views nunca renderizou um layout: `@extends("layouts.app")`
  entregava a notação de ponto crua ao Jinja, e o erro era engolido por um
  placeholder `<div>Rendered view: x</div>` com HTTP 200.
- `EventDispatcher.listen(Evento, UmListener)` exigia lista e levantava
  `TypeError`; listeners de classe base não ouviam subclasses.
- `ModuleManager.enable()/disable()` retornavam `True` mesmo para módulo
  inexistente.
- `PluginManager.trigger_hook()` engolia exceção de plugin sem registrar nada.
- `FacadeMeta.__getattr__` fabricava qualquer atributo, inclusive dunders,
  resolvendo o container antes do boot.
- `Container.__init__` reivindicava o singleton global incondicionalmente: uma
  segunda `Application` sequestrava o processo.
- Middleware era instanciado a cada request, recriando o store de sessão e sua
  chave de assinatura — nenhum cookie sobrevivia.
- `captcha.py` usava `Any` sem importar: passava no Python 3.14 (anotações
  lazy, PEP 649) e quebrava no 3.11, o mínimo declarado.
- Migration `framework_dynamic_tables`: `role_user` usava `uuid` para `user_id`
  e `permission_role` era dropada no `down()` mas nunca criada no `up()`.
- Migration `jobs`: `available_at`/`created_at` como INTEGER recebendo string
  ISO.
- 4xx eram logados com traceback completo, enterrando as falhas reais.
- `datetime.utcnow()` deprecado no Python 3.12+.

**Documentação**

- `security.md` afirmava que os cookies de sessão eram assinados com
  criptografia pós-quântica e "não podem ser lidos". Ambos falsos: a assinatura
  é HMAC-SHA256 e, no driver de cookie, o payload é legível pelo cliente
  (assinado, não criptografado).
- API do Captcha documentada com assinatura errada.

### Alterado

- O locale `pt` era português brasileiro rotulado como genérico ("Painel de
  Controle", "Baixar", "Registrar"). Agora `pt` é português europeu e `pt-BR` é
  brasileiro, com textos distintos.
- `QueueManager` era falso: montava um payload com as chaves `"TestJob"` e
  `"999"` hardcoded para o teste passar. Reescrito com serialização real.
- `Captcha.validate` tinha `and code != "WRONG"` hardcoded. Agora usa
  `secrets.compare_digest` e limpa o código sempre (single-use).
- Containers renomeados para `framework` e `framework-db`; projeto Compose
  fixado em `name: framework`. O banco de dev ganhou volume nomeado — antes
  ficava na camada do container e sumia a cada recriação.
- Dependências enxugadas: saíram `sqlalchemy`, `alembic`, `pydantic`,
  `pydantic-settings` e `click`, nenhuma usada. `pytest` e `httpx` viraram
  extra `[dev]`.
- `bcrypt` fixado em `<4.1`: acima disso o passlib quebra (`__about__` foi
  removido).
- `pyproject.toml`: entrypoint passou a ser `craft = services.cli.app:main`.
- Repositório passou a ser versionado (`git init`).

### Removido

- Domínio SoftPax (funerária/cemitério) do esqueleto base: 16 migrations,
  18 models, 26 controllers e 3 pastas de views.
- Arquivos mortos: `app/main.py` (uma app FastAPI paralela), `home_controller.py`,
  `BaseModel.py` (models SQLAlchemy), `services/coreengine/` e 4 arquivos vazios
  sem nenhuma referência.
- Landing page `codepy-showcase` (vite) da raiz.
- `.agents/.agents/` e `.ai/.agents/`, diretórios aninhados recursivamente.
  O `changelog.md` que vivia no aninhamento foi perdido nessa limpeza; este
  arquivo recomeça a partir do histórico do Git.

**Projeto open source**

- Licença **MIT** (`LICENSE`), © 2026 Antonio Santos.
- Metadados de autoria, classificadores e URLs no `pyproject.toml`;
  `__author__`, `__email__`, `__license__` e `__copyright__` no pacote.
- Cabeçalho de licença em 134 arquivos-fonte.
- `CONTRIBUTING.md` e `SECURITY.md`, com checklist de produção e as lacunas
  conhecidas declaradas em vez de escondidas.
- Documentação completa em `documentation/`: 17 guias com índice, cobrindo
  instalação, configuração, container, rotas, controllers, views, validação,
  migrations, ORM, segurança, sessões, cache, filas, resources, i18n, testes,
  deploy e a referência do `craft`. As 130 APIs citadas foram verificadas
  contra o código.

### Notas de compatibilidade

- **Python 3.11+**. A suíte roda no 3.14 local e no 3.11 do container.
- Mixins de soft delete precisam vir **antes** do `Model` na declaração
  (`class Note(SoftDeletes, Model)`), senão o MRO faz o `Model` ganhar.
- Aplicações que dependiam do `pt` com texto brasileiro devem passar a pedir
  `pt-BR`. O fallback `pt-BR → pt → en` cobre chaves ausentes.
