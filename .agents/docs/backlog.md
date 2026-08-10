# Backlog — Craft Framework (base para novas aplicações)

> Contexto: este repositório é o **framework base** usado para criar novas aplicações
> (o esqueleto que se copia para iniciar uma app), não uma aplicação de negócio.
>
> ⚠️ **2026-08-11 — falha de segurança encontrada em uso, não por teste:**
> `GET /admin` (lista todos os usuários, administradores e tenants) carregava
> só o alias `auth`. Qualquer conta que fizesse login lia o diretório inteiro.
> Fechado no commit `0808161`, com guarda estrutural: toda rota sob `/admin`
> precisa declarar um alias que autoriza, e a suíte falha se alguma não
> declarar. Lição registrada: comparar declarações de rota no olho não é
> controle.
>
> Estado: **823/823 testes passando** em SQLite e em PostgreSQL real, no Python
> 3.11 do container, com `ruff check .` limpo. Cada arquivo de teste também
> passa isolado — nenhum depende da ordem. App real validado em
> `http://localhost:8300`, incluindo o fluxo de login com CSRF e captcha,
> headers de segurança confirmados ao vivo.
>
> ⚠️ O motor foi renomeado de `services/` para **`engine/`** (importado como
> `craft.*`). Referências a `services/` mais abaixo neste arquivo são registro
> histórico — o path atual é `engine/`.

## 🔬 Benchmark e stress test (2026-08-07)

Relatório completo em [`benchmark-2026-08-07.md`](benchmark-2026-08-07.md):
teste de carga real + 4 auditorias especializadas (segurança,
performance/escalabilidade, CI/CD/DX, UI/UX) contra código real, comparadas
com Laravel/Django/Rails/FastAPI. 26 achados no total.

**Corrigido no mesmo dia** (4 agentes em paralelo, revalidado com
`pytest` + checagem ao vivo no container):

- ✅ `/admin` agora renderiza o template real (`admin.dashboard`) em vez do
  `<h1>` hardcoded.
- ✅ Rotas de escrita do CRUD builder exigem autenticação de verdade
  (`write_middleware=["api", "auth"]`, não só `"api"` que nunca bloqueava) e
  o `FormRequest.authorize()` gerado checa usuário autenticado em vez de
  sempre `True`.
- ✅ Fluxo de validação do blog (posts) corrigido — redisplay com erros e
  input preservado, `_old_input` agora é populado de verdade.
- ✅ Mass assignment invertido para fail-closed (`fillable` vazio = nada
  gravável, era o oposto).
- ✅ `SecurityHeaders` middleware novo (X-Content-Type-Options, X-Frame-Options,
  Referrer-Policy), `APP_KEY` vazio em produção agora falha o boot em vez de
  degradar em silêncio, `docker-compose.prod.yml` não tem mais senha padrão
  conhecida, `SECURITY.md` corrigido (afirmava não ter rate limiting — tem).
- ✅ CI agora testa Python 3.11/3.12/3.13 × PostgreSQL real (antes: só
  3.11 × SQLite), `ruff` e `pytest-cov` adicionados.
- ✅ `Dockerfile.prod` sem branding "Codepy" residual, ganhou passo de
  migração antes do boot do gunicorn.
- ✅ CRUD builder: linhas de campo preservadas em falha de validação, labels
  de acessibilidade adicionados, `per_page` sem limite agora capado em 100.
- ✅ Sistema de tokens CSS unificado (`app.css` duplicava paleta em vez de
  reusar `craft-theme.css`), `posts/show.forge.py` limpo de classes órfãs.

**Deliberadamente NÃO corrigido — precisa de fatia própria:**

- ✅ **Teto de concorrência resolvido em 2026-08-10** (ver a seção própria mais
  abaixo). O registro original dizia:
  🔴 **O teto de concorrência medido (~30 req/s constante, independente de
  1 ou 100 clientes) continua lá.** Um agente tentou o pool de conexão e
  parou de propósito: `Connection` mistura a conexão bruta com estado
  mutável por-requisição (profundidade de transação, schema de tenant
  ativo) — resolver isso direito exige lifecycle de conexão por-requisição,
  não uma troca local. Toca `DatabaseManager`, `Connection`, middleware de
  tenant, o migrator e `conftest.py`. Decisão certa foi parar em vez de
  arriscar um "passa nos testes, quebra em produção" — mas o problema real
  segue sem solução. Ordem obrigatória quando essa fatia for feita: pool de
  conexão → offload de thread → `--workers` no `dev.py serve`. Nunca threading
  sem pool primeiro (corrompe cursor sob concorrência real).
- ✅ **Item 4 resolvido (2026-08-07, fatia própria)**: CRUD builder agora
  gera UI admin de verdade por padrão — lista paginada + form de criar/editar
  com `old()`/erros de validação, controller HTML dedicado em
  `Admin/<Entity>AdminController.py`, registrado em `/admin/<slug>` atrás de
  `auth`. Convive sem colisão com a API JSON existente (nomes de classe,
  arquivos e rotas distintos, confirmado por teste). Validado ao vivo: gerado
  `Product`, migrado, gate de auth confirmado (302 sem login). 641/641 testes
  (+8 novos). Limpo depois — nenhum resíduo de `Product` ficou no repo.
- ✅ **RBAC funcional (2026-08-07)**: `has_role()`, fallback de permissão no
  `Gate.allows()`, middleware `role:<slug>`/`permission:<slug>` (alias
  parametrizado novo no kernel), CLI (`role:*`, `permission:*`,
  `user:assign-role`), UI admin em `/admin/roles`/`/admin/permissions`.
  Os 3 logins demo (`user@craft.local`, `tenant@craft.local`,
  `admin@craft.local`, senha `craft` para todos) agora são oficialmente
  documentados no `README.md` como credenciais padrão do framework — o
  usuário `tenant` que não tinha nenhum papel atribuído ganhou o papel novo
  `tenant-manager`, fechando a escada de 3 níveis. Dois bugs reais
  encontrados e corrigidos durante a validação (não pelo agente que
  implementou — só apareceram ao rodar a suíte completa):
  1. Alias parametrizado usado sem parâmetro (`"role"` em vez de
     `"role:admin"`) estourava `TypeError` cru em vez de `KeyError`
     acionável.
  2. **Poluição de teste entre arquivos**: `test_framework.py` substituía
     `modules`/`translations` por schema reduzido e nunca restaurava —
     como o banco de teste é compartilhado (session-scoped), todo arquivo
     que rodasse depois (em ordem alfabética, antes do workaround não
     relacionado do `test_subsystems_persistence.py`) via o schema quebrado.
     `test_rbac.py` só falhava como parte da suíte completa, nunca isolado
     — exatamente o tipo de bug que o `CONTRIBUTING.md` pede para nunca
     acontecer. Corrigido na origem.
  658/658 testes. Validado ao vivo: CLI `role:list`/`permission:list`
  mostrando a escada de 3 níveis, `/admin/roles` redirecionando sem login.
- CRUD builder ainda sem reordenar linhas de campo (só adicionar/remover).
- Sem validação client-side no formulário do CRUD builder antes do submit.
- ✅ **Hero da landing page corrigido (2026-08-08)**: `.hero-section` era
  `flex-direction: column` fixo — nunca formava duas colunas em nenhuma
  largura, sempre empilhado e centralizado (era exatamente a queixa: "não
  forma largura da tela"). Agora grid real: 1 coluna até 1024px, 2 colunas
  (texto + preview de código) a partir daí. Validado com navegador headless
  de verdade (não só pytest) em 1440px e 390px.
  - **Achado no processo**: a correção anterior de "unificar tokens CSS"
    (sessão passada) tinha editado `public/css/app.css` — arquivo que
    **nunca foi carregado por nenhuma view**. A página real usa
    `assets/css/craft-components.css`, cópia quase idêntica mas separada.
    Arquivo morto removido; a correção do hero foi no arquivo certo.
    Lição: mudança de CSS/UI não é validada por `pytest` (nenhum teste
    renderiza página) — precisa de checagem visual real.
  - 🔭 De passagem: no mobile (390px), a barra de navegação do header
    (`layouts/app.forge.py`) não tem menu hambúrguer — os links (EN/PT/
    PT-BR/ES, Fórum, Aprender...) simplesmente quebram linha/cortam.
    Não corrigido — fora do pedido desta sessão.
- ✅ **Bug de dark mode corrigido (2026-08-08)**: usuário reportou "totalmente
  distorcida" comparando com codeigniter.com — investigando com
  `prefers-color-scheme: dark` forçado no navegador, achei a causa real:
  `--bg-body`/`--bg-section` usavam os tokens semânticos que trocam pra
  escuro corretamente, mas todo o texto da landing page usa passos
  literais de cinza que nunca trocam — fundo escurecia, texto continuava
  escuro, várias seções ficavam ilegíveis. Fixado o fundo no claro
  (a página nunca teve paleta escura própria — decisão explícita de
  single-theme, não meio-termo quebrado). Suspeita: é isso que o usuário
  viu, se o sistema dele está em dark mode — outra hipótese é cache do
  navegador não invalidando o CSS antigo (versão do app não mudou).
- ✅ **Hero ainda não era largura total, de verdade (2026-08-08)**: usuário
  mandou screenshot mostrando o hero em duas colunas mas preso numa caixa
  estreita, vazio grande nos dois lados. Causa: `layouts/app.forge.py`
  já embrulha tudo em `max-w-7xl` (1280px), e o `.hero-section` tinha
  outro `max-width:1120px` por dentro disso — duas caixas aninhadas.
  Corrigido separando em duas camadas (mesmo padrão que o resto da página
  já usa): `.hero-section` agora fura a restrição do ancestral com a
  técnica padrão de full-bleed (`margin-inline: calc(50% - 50vw)`), fundo
  ocupa a largura real da tela; o grid de conteúdo foi para um `.hero-inner`
  novo, continua limitado a 1120px e centralizado. Efeito colateral
  conhecido da técnica (unidade `vw` inclui a barra de rolagem, gerava uns
  pixels de overflow horizontal) resolvido com `overflow-x:hidden` no
  `body` — correção padrão, não gambiarra. Validado em 1920px, 1440px e
  390px com navegador de verdade.

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

## ✅ Erradicação de placebos (2026-08-10)

Princípio adotado pelo usuário como regra permanente: **o que o framework
promete ao desenvolvedor, ele tem que entregar.** Quatro varreduras sucessivas
contra o código real; a quarta veio praticamente limpa. ~30 placebos
eliminados, cada um com teste de regressão. Detalhe linha a linha no
`CHANGELOG.md`.

Um placebo é código que *parece* implementado visto de fora — nome de método,
docstring, config declarada, comando de CLI, diretiva de template — e que
retorna valor fixo, engole exceção fingindo sucesso, ignora argumentos ou
nunca é invocado.

**Segurança:**

- `AuthenticateApiToken` nunca rejeitava — resolvia o usuário se o token
  casasse e seguia adiante de qualquer forma. Toda rota com o alias `api`
  aceitava anônimo. E o guard não tinha coluna: `api_token` não existia em
  migration nenhuma.
- `/admin/crud-builder` protegido só por `auth` — a rota escreve `.py` e
  reescreve `routes/`. Era RCE para qualquer usuário registrado.
- `make policy` gerava política com `return True` em tudo, inclusive `user=None`.
- `unique`/`exists` falhavam em aberto: qualquer erro de banco fazia a regra
  passar (`unique:userz,email` validava e o duplicado entrava).
- Agregados (`count`/`sum`/…) interpolavam a coluna sem allowlist.

**Funcionalidade quebrada em silêncio:**

- Method spoofing nunca funcionou: o `_method` era emitido em dois lugares e
  lido em nenhum, então todo edit/delete gerado dava 405 e `@method` era HTML
  decorativo. Resolvido na camada ASGI (o Starlette roteia por método antes).
- `support.view()` engolia toda exceção e devolvia HTTP 200 com
  `"View x rendered"`.
- `Schema.table()` descartava índices; `enum()` não restringia nada.
- `Model.roles()` na classe base devolvia papéis de *usuário* para qualquer
  modelo (movido para `User`/`Role`).
- `url_for()` fabricava `/nome.da.rota` para rota inexistente.
- Falha ao sondar colunas era cacheada para sempre, desligando o UUID público.
- `Auth.once()` não autenticava ninguém; `Facade._swap()` era `pass`.
- Scheduler era stub (`hourly()` retornava `self`) e `register_console()` nunca
  era chamado — ver `engine/schedule/`.

**Config decorativa:** `config/logging.py` inteiro ignorado, os três feature
flags não ligavam nada, `app.debug` nunca resolvia (debug jamais ligava),
`app.release` inexistente, `retry_after` hardcoded.

**Lição registrada:** um teste existente (`test_once_authenticates_without_persisting`)
**codificava o bug** em vez do contrato — exigia `guest() is True` depois de
`Auth.once()`. Vale auditar outros testes com a mesma pergunta: fixam a promessa
ou o comportamento que existia?

## 🧭 Épico registrado (2026-08-10) — Hardening + Craft AI Engine

Pedido do usuário, registrado como escopo grande a ser fatiado. **Nada
executado ainda** — isto é só o registro.

Referência de aprendizado: repo `odysseus-dev/odysseus`, cópia local em
`.claude/Project Reference` — extrair padrões de motor de inferência,
adaptadores de modelo, orquestração de workspace, fluxos de automação e
integração de agentes. Referência, não código a copiar.

### E1. Revisão e modernização do Python core
- Revisar o código Python de todo o framework (`services/` primeiro, depois `app/`).
- Aplicar práticas modernas: typing completo, async onde faz sentido, context
  managers, dataclasses, `match`, hierarquia de exceções melhor.
- Remover padrões datados e degradação silenciosa remanescente.

### E2. Hardening de segurança (todas as camadas)
- Router, middleware, ORM, motor de views (Forge), auth, autorização,
  sessão/token, fronteira de módulos e plugins.
- Levantar vulnerabilidades, padrões inseguros e validações fracas; corrigir
  com teste que prove a correção.
- Segredos: manuseio seguro, sem default conhecido, sem vazamento em log.
- Entregável: lista de vulnerabilidades encontradas × correção aplicada.

### E3. Craft AI Engine — inferência nativa
- Interface unificada para qualquer LLM, local ou remoto.
- Adaptadores nativos: Anthropic, OpenAI, Gemini, DeepSeek, Groq e afins.
- Suporte a runners locais / inferência local.
- Agentes de automação, tool-calling e orquestração de workflow.
- Documentação + exemplos para estender via plugin/módulo (o `PluginManager`
  DB-backed da Fatia 3 é a base natural do ponto de extensão).

### E4. Cloud e storage
- Validar/implementar drivers: FS local, NFS, Amazon S3.
- Fluxos seguros de upload/download; abstração de driver preparada para novos
  provedores; storage criptografado.

### E5. Entregáveis de saída
- Revisão detalhada da arquitetura atual.
- Vulnerabilidades × correções.
- Propostas de features Python novas e melhorias.
- Propostas de evolução do motor de inferência, integrações e abstrações.
- Melhorias de documentação.

**Pré-requisito de ordem: atendido.** O teto de concorrência tocava o E3
diretamente — inferência é I/O-bound e empilha requests longos. O pool de
conexão + threadpool + `--workers` foram entregues em 2026-08-10, então o AI
Engine já pode ser exposto sob carga.

## 🔜 Próximas fatias

Ordenadas por impacto. Revisadas em 2026-08-10 — itens que já haviam sido
resolvidos e continuavam listados como pendentes foram removidos (rate limiting
via `ThrottleRequests`, `_old_input`, `per_page` capado, headers de segurança).

### O que sobrou, priorizado (resumo)

Leia isto primeiro; o detalhe de cada um está logo abaixo.

| # | Item | Por quê |
|---|---|---|
| ✅ 1 | ~~Teto de concorrência~~ | **Resolvido (2026-08-10)** — pool → threadpool → workers, nessa ordem. Medido: 27 req/s constante → ~115 req/s a partir de 10 clientes, p95 de 1.9s para 0.57s. |
| 🟠 2 | **Storage/S3, SMTP/mail, API manager** | Os três da lista original do usuário que ainda **não existem**. A decisão do S3 já está tomada: `boto3` como extra opcional. |
| ✅ 3 | ~~`engine/orm/__init__.py` vazio~~ | **Resolvido (2026-08-10)** — exporta `Model`, `QueryBuilder`, `SoftDeletes`, relações e exceções, com teste. |
| 4–10 | Eager loading aninhado, remember-me/reset de senha, cifra de sessão, Redis na fila, decisão do FastAPI | Melhorias e dívida acumulada, nenhuma bloqueante. Lacunas de doc e dívidas menores: **fechadas em 2026-08-10**. |
| 11 | **Auditar testes que fixam comportamento em vez de promessa** | A erradicação de placebos achou um teste que codificava o próprio bug. Provavelmente não é o único. |

### ✅ 1. Teto de concorrência (resolvido em 2026-08-10)

Era **~27 req/s constante de 1 a 50 clientes** — a assinatura de um processo que
atende uma requisição por vez. Agora **~115 req/s a partir de 10 clientes**,
p95 de 1.9s → 0.57s, zero falhas. Medido com `tools/loadtest.py` (novo, só
stdlib), antes e depois, alternando só o offload. A ordem obrigatória foi
seguida à risca:

1. **Pool de conexão** (`engine/orm/connection.py`). O modelo é *checkout no
   primeiro uso, devolução no fim do request* (`release()`, chamado pelo
   kernel). `pool_size` (padrão 10) e `pool_timeout` (padrão 30s) por conexão;
   esgotamento levanta erro nomeando a config em vez de travar.
   - **Erro cometido e corrigido no caminho:** a primeira versão dava uma
     conexão permanente por thread, sem devolução. Isso não é pool — acumula
     uma conexão por thread até o PostgreSQL responder *"sorry, too many
     clients already"*, que foi exatamente o que a suíte fez. Só apareceu no
     PostgreSQL e só na suíte completa.
2. **Estado por request saiu dos singletons.** Profundidade de transação e
   `search_path` de tenant passaram a pertencer à conexão emprestada; usuário
   e sessão do `AuthManager` viraram thread-local. Os dois eram globais de
   processo — sob concorrência isso não é corrida, é falha de correção: um
   tenant repontando o schema no meio da query de outro, e a identidade de um
   visitante visível no request de outro. `release()` também limpa o tenant.
3. **Offload no kernel** (`run_in_threadpool`), devolvendo a conexão dentro da
   thread que a pegou emprestada.
4. **`dev.py serve --workers N`**, que recusa fingir: `--workers` com
   `--reload` é impossível no uvicorn, então avisa e serve com 1.

Provado por `tests/test_connection_concurrency.py` com threads de verdade:
isolamento de sessão, de transação, de schema de tenant (em PostgreSQL real),
de identidade, reuso do pool, crescimento limitado, esgotamento e rollback de
transação abandonada na devolução. Sob 50 clientes, `pg_stat_activity` mostra
11 conexões (10 do pool + 1 administrativa) — o limite é respeitado.

Desbloqueia o E3 (AI Engine): inferência é I/O-bound e vai empilhar requisições
longas.

### 🟠 2. Subsistemas que o `CRAFT_DESIGN.md` promete e não existem

Nenhum destes existe em `engine/` — o doc de design os descreve como se
existissem (hoje marcados como "planned" na árvore, mas ainda não construídos):

- **Storage / filesystem** — nenhuma abstração de disco. Decisão já tomada com o
  usuário: driver local sempre disponível (stdlib), S3 via `boto3` como *extra*
  opcional no `pyproject` (`pip install craft[s3]`), importado só quando o driver
  `s3` é usado.
- **Mail / SMTP** — zero `smtplib` no projeto.
- **API manager** — não existe módulo. Hoje há `Route.api_resource` +
  `AuthenticateApiToken` (agora funcional, ver erradicação de placebos). Faltam
  emissão/rotação de chaves, versionamento e rate-limit por cliente.
- `broadcast/`, `notification/` — sem código.

### ✅ 3. `engine/orm/__init__.py` (resolvido em 2026-08-10)

Estava vazio — único subpacote assim, quebrando o `from craft.orm import Model`
que `documentation/orm.md:12` ensina. Repopulado: `Model`, `QueryBuilder`,
`DatabaseManager`, `Connection`, `Row`, `SoftDeletes`, as quatro relações e as
quatro exceções do ORM, com teste que exige que todo nome de `__all__` resolva.

### 4. Eager loading aninhado e sob demanda

`with_()` cobre um nível. Faltam `with_("posts.comments")` (aninhado),
`Collection.load("posts")` (carregar depois da query) e `with_count()`.

### 5. Remember-me e reset de senha

`attempt()` não tem `remember` (removido em vez de fingir que funcionava) e não há
fluxo de recuperação de senha nem verificação de e-mail. O fluxo de reset depende
do subsistema de mail (item 2).

### 6. Criptografia de sessão

O driver `cookie` assina mas **não criptografa** — o payload é legível pelo
cliente. Hoje a orientação é usar `SESSION_DRIVER=file` para dados sensíveis;
adicionar cifra ao driver de cookie fecharia a lacuna.

### 7. Filas

Drivers `database` e `sync` existem. Falta Redis (hoje `QUEUE_CONNECTION=redis`
avisa e cai para `database` — honesto, mas não implementado), `failed_jobs`
persistida e worker com múltiplos processos.

### ✅ 8. Documentação com lacunas verificadas (fechada em 2026-08-10)

Auditada de novo contra o código; a maior parte da lista de 2026-08-08 já havia
sido corrigida em sessões anteriores e continuava marcada como pendente
(`self.faker` em `migrations.md`, `response()` em `security.md`, usuário `dev`
em `installation.md`, versão `0.x` no `SECURITY.md` — nenhum existe mais).
O que de fato faltava, e foi feito agora:

- `orm.md` ganhou **Eager loading** e **Soft deletes** (mais many-to-many com
  `attach/detach/sync`). `resources.md:133` já linkava `orm.md#eager-loading`,
  seção que não existia. Os limites atuais estão escritos: um nível só, sem
  `with_("posts.comments")`, sem `collection.load()`, sem `with_count()`.
  A armadilha de MRO do `SoftDeletes` está documentada como o `TypeError` que
  hoje ela levanta.
- `crud-builder.md` entrou no índice (`documentation/README.md`), e o link
  quebrado `orm.md#query-builder` virou `#querying--filtering`.
- Contagem de testes do `README.md` atualizada (765 → 775). Os números do
  `CHANGELOG` são registro histórico e ficam como estão.

### ✅ 9. Dívidas menores (fechadas em 2026-08-10)

- `ruff check . || true` no CI: `ruff` rodado no container (que tem o extra
  `[dev]`), 9 achados, todos corrigidos — 6 `raise ... from None` na CLI, uma
  variável de loop não usada, um `getattr` constante e um `zip()` sem `strict`.
  Com a base limpa, o `|| true` foi removido: o lint agora reprova o build.
- `engine/http/kernel.py` não consulta mais o banco por request: pergunta ao
  `ModuleManager`, que cacheia por `cache_ttl` (5s) e invalida no
  `enable()`/`disable()`. `ModuleManager.state()` novo devolve `None` para
  módulo desconhecido (≠ `False`), preservando o fallback para
  `modules.<slug>.enabled` no config. Contagem de queries em
  `tests/test_module_state_cache.py`.
- `PostController.show()/update()` agora usam `.response()`, como o `store()`.
- Config morta resolvida por decisão explícita: `APP_URL` passou a ser lido pelo
  `Router.absolute_url_for()` (novo); `auth.defaults.guard` + `provider` de cada
  guard passaram a escolher de verdade o model, via
  `AuthManager.provider_name()`; **`APP_TIMEZONE` e `password_timeout` foram
  removidos** — o framework grava tudo em UTC por design e não tem janela de
  confirmação de senha, então eram botões sem fiação.

**Achado do dia, fora da lista:** o `Dockerfile` e o `Dockerfile.prod` ainda
copiavam `services/`, então `docker compose up --build` falhava desde o rename
para `engine/`. O container de dev seguia de pé só porque nunca fora
reconstruído — e o bind mount dele apontava para `D:\data\www\craft framework`,
caminho que não existe mais. Corrigido e revalidado: 775 testes em SQLite e em
PostgreSQL real, app respondendo em `http://localhost:8300`.

### 10. Decisão pendente: FastAPI

O framework é construído **diretamente sobre Starlette** — `fastapi` está nas
dependências (`pyproject.toml:33`) e no nome do projeto, mas não é importado em
lugar nenhum. Peso morto no `pip install`. Manter por identidade ou remover por
honestidade é uma decisão sua.

### 11. Auditar testes que fixam comportamento em vez de contrato

A erradicação de placebos achou um teste que **codificava o bug**
(`test_once_authenticates_without_persisting` exigia `guest() is True` depois de
`Auth.once()`, tornando `once()` idêntico a `validate()`). Vale uma passada
perguntando de cada teste: ele afirma a promessa, ou o comportamento que existia
quando foi escrito?

### 6. Documentação

`CRAFT_DESIGN.md` (74 KB) ainda descreve o desenho antigo. O `README.md` e
`documentation/*.md` foram atualizados.

**Fatia em andamento (2026-08-07), checkpoint 1/4 concluído:**

- ✅ Skill nova `.agents/skills/project/workspace-architecture/SKILL.md` —
  contrato do split raiz-do-workspace vs `data/` (o que é montado no
  container) e o procedimento para clonar isto e iniciar uma nova app.
- ✅ `.agents/skills/project/scaffolding/SKILL.md` corrigida — descrevia um
  serviço Compose (`craft-app`), porta e `DB_CONNECTION` que não existem mais
  desde a reorganização para `data/`.
- ✅ `README.md` na raiz do workspace, apontando para `data/README.md` e para
  as skills acima.
- ✅ Fatia 2: `documentation/*.md` auditada linha a linha contra o código
  (achou e corrigiu 2 mentiras: SQLAlchemy no ORM, PQC na sessão).
  `CRAFT_DESIGN.md` ganhou banner deixando claro que é visão aspiracional, não
  o implementado. Português residual traduzido (README/CHANGELOG/SECURITY do
  `data/` + 5 docstrings). 41 arquivos em `services/` ganharam o cabeçalho de
  orientação `Category/Relations/References`. Achado não corrigido (fora do
  escopo desta fatia): `resources/views/{access,dashboard,layout}` e
  `admin/translations/index.forge.py` ainda são views órfãs do domínio
  SoftPax em português, apesar do CHANGELOG dizer que o domínio foi removido —
  decidir se apaga ou mantém como demo.
- ✅ Fatia 3: `PluginManager` nivelado ao `ModuleManager` — migração
  `plugins` (id, name, slug único, enabled, path, timestamps), model
  `app/Models/Plugin.py`, descoberta em disco (`plugins/<slug>/plugin.py`
  expondo um dict `PLUGIN`), persistência via `installed()/is_enabled()/
  enable()/disable()` (mesmo padrão try-DB-fallback-memória do
  ModuleManager, nunca finge sucesso), `sync()` faz upsert sem reativar
  plugin que o operador desligou. CLI: `plugin:list|enable|disable|sync`.
  Testes novos em `tests/test_plugins.py`. Suíte completa: **612 passed**
  (rodado no container, Python 3.11). Decisão tomada: o `all()` antigo
  (registro de hooks em memória) foi mantido como está — a listagem
  DB-backed ganhou o nome `installed()` para não quebrar os testes
  pré-existentes de hooks.
- ✅ Fatia 4: CRUD builder — `services/cli/crud_builder.py` gera migration +
  model + FormRequest + Resource + controller (ligado de verdade ao ORM, não
  placeholder) a partir de `dev.py make crud <Entity> --fields "nome:tipo:
  regra1|regra2,..."`. Tela admin em `/admin/crud-builder` (atrás de `auth`,
  igual `/admin`) chama o mesmo `build_crud()`. Documentado em
  `documentation/crud-builder.md`. Suíte: **627 passed** (612 + 15 novos).
  Validado ao vivo: gerado `Product`, migrado, `GET/POST /api/v1/products`
  respondendo de verdade no container.
  - **Bug real encontrado e corrigido no smoke test**: `dev.py` dividia
    *qualquer* argumento com `:` em dois tokens — isso quebrava
    `--fields "name:string:required,..."`. Corrigido para só dividir o
    primeiro token (o comando), preservando `migrate:status`/`plugin:list`.
  - **Correção de design**: a rota gerada foi registrada em `routes/api.py`
    (via `Route.api_resource(..., write_middleware="api")`, mesmo padrão do
    `PostController`) em vez de `routes/web.py` — o controller só devolve
    JSON e `web.py` exige CSRF, que um cliente de API não tem como satisfazer
    (a primeira versão gerada caía em 419 nesse smoke test).
  - **Limite documentado, não corrigido**: o controller gerado não chama
    `Gate.authorize(...)` como o `PostController` faz — então as rotas de
    escrita de uma entidade gerada ficam abertas até o dev adicionar uma
    Policy. Está explícito em `documentation/crud-builder.md`.
