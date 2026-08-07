# Codepy

Um framework web Python completo, construído sobre **Starlette**. Este repositório é o **esqueleto base** para criar novas
aplicações — o o esqueleto que se copia para iniciar uma app.

O core vive em `services/` e é exposto publicamente como `codepy.*`.

```python
from codepy.facades import Route, DB, Auth
from codepy.orm.model import Model
```

**394 testes**, validados em SQLite, PostgreSQL e Python 3.11.

---

## Começando

```bash
cp .env.example .env
python craft.py key:generate        # assina os cookies de sessão
python craft.py migrate --seed
python craft.py serve
```

Ou com Docker (app em `http://localhost:8300`):

```bash
docker compose up -d --build
```

---

## O CLI `craft`

```bash
python craft.py migrate                 # aplica migrations pendentes
python craft.py migrate:status          # o que rodou e em qual batch
python craft.py migrate:rollback        # reverte o último batch
python craft.py migrate:fresh --seed    # dropa tudo, recria e popula
python craft.py db seed                 # roda o DatabaseSeeder
python craft.py db show|tables|ping     # inspeciona a conexão
python craft.py route list              # todas as rotas registradas
python craft.py make model Product -m   # model + migration
python craft.py make controller Product -r
python craft.py queue work              # processa a fila
python craft.py tinker                  # shell com a app carregada
```

Aceita as duas formas: `migrate:status` e `migrate status`.

---

## Estrutura

```
app/                     Código da aplicação
  Http/Controllers/      Controllers
  Http/Middleware/       Middleware
  Http/Requests/         FormRequests (autorização + validação)
  Http/Resources/        Transformers JSON
  Models/                Models Codepyquent (Active Record)
  Policies/ Events/ Listeners/ Jobs/ Providers/ Services/
bootstrap/app.py         Cria o container, registra providers, monta o kernel
config/                  app, auth, cache, database, logging, queue, session
database/                migrations/ seeders/ factories/
public/index.py          Front controller (`application = asgi_app`)
resources/views/         Templates Forge
routes/                  web.py, api.py, console.py
services/                O framework (exposto como codepy.*)
storage/                 logs, cache e sessões
tests/                   Suíte pytest
craft.py                 CLI
```

---

## Banco de dados

Três drivers, com o mesmo SQL: **SQLite**, **PostgreSQL** e **MySQL**. Os
placeholders `?` e `:nome` são traduzidos para o paramstyle de cada driver, e o
schema builder gera DDL por dialeto.

```python
# database/migrations/2026_01_01_000001_create_products_table.py
from codepy.migrations import Schema

def up():
    Schema.create_table("products", lambda t: (
        t.id(),
        t.string("name"),
        t.decimal("price", 10, 2),
        t.foreign_id("user_id").constrained().cascade_on_delete(),
        t.boolean("active", default=True),
        t.timestamps(),
    ))

def down():
    Schema.drop_table("products")
```

Os estilos fluente e keyword são intercambiáveis:
`t.string("cpf").nullable()` == `t.string("cpf", nullable=True)`.

Split de leitura/escrita e schema-por-tenant (PostgreSQL) são suportados:

```python
DB.set_tenant_schema("tenant_42")
```

---

## ORM (Codepyquent)

```python
class Post(Model):
    __table__ = "posts"
    fillable = ["title", "body", "user_id"]

    def author(self):
        return self.belongs_to(User, foreign_key="user_id")

    def comments(self):
        return self.has_many(Comment, foreign_key="post_id")
```

**Eager loading** — `with_()` transforma N+1 em uma query por relação:

```python
posts = Post.with_("author", "comments").get()   # 3 queries, não 1 + 2N
for post in posts:
    post.author().first()    # já carregado
```

Relações: `has_one`, `has_many`, `belongs_to`, `belongs_to_many`
(com `attach`/`detach`/`sync`). Soft deletes via mixin — **liste o mixin
primeiro**, senão o MRO faz o `Model` ganhar:

```python
class Note(SoftDeletes, Model):
    __table__ = "notes"

Note.query()          # esconde os deletados
Note.with_trashed()   # inclui
Note.only_trashed()   # só os deletados
```

Query builder: `where`, `or_where`, `where_in`, `where_null`, `where_between`,
`join`, `group_by`, `having`, `order_by`, `paginate`, e agregações
(`count`, `sum`, `avg`, `min`, `max`).

---

## HTTP

```python
Route.get("/posts", [PostController, "index"]).name("posts.index")
Route.post("/posts", [PostController, "store"]).middleware("auth")
Route.resource("posts", PostController)
```

Middleware por rota resolve por alias: `auth`, `api`, `session`, `csrf`.
Um alias desconhecido **levanta erro no boot** em vez de virar proteção
decorativa.

O pipeline global fica em `bootstrap/app.py`, e a ordem importa — a sessão
precisa existir antes do CSRF e antes de resolver o usuário:

```python
kernel.with_middleware(StartSession, VerifyCsrfToken, Authenticate, ...)
```

### Request

O corpo é parseado antes do pipeline, então controllers síncronos leem input
direto:

```python
request.input("email")      # query string + corpo (form ou JSON)
request.only("name", "email")
request.boolean("remember")
request.file("avatar")
request.session().get("cart")
request.user()
request.bearer_token()
```

---

## Sessão e CSRF

Dois drivers: `cookie` (payload no cookie assinado) e `file` (só o id no
cookie, payload em disco — permite invalidação server-side). Ambos assinam com
o `APP_KEY`; cookie adulterado é rejeitado, não confiado.

```python
request.session().put("cart", [1, 2])
request.session().flash("status", "Salvo!")   # vive exatamente um request
request.session().token()                      # token CSRF
```

CSRF é verificado em POST/PUT/PATCH/DELETE, via campo `_token` ou header
`X-CSRF-TOKEN`. Rotas `api/*` são isentas por padrão. Falha devolve **419**.

---

## Autenticação

```python
if Auth.attempt({"email": email, "password": password}):
    return redirect(route="home")
```

Senhas usam bcrypt (com fallback PBKDF2-SHA256 se o backend não estiver
disponível). O login é gravado na sessão e o id da sessão é rotacionado, o que
fecha session fixation. Um usuário inexistente custa o mesmo tempo que uma senha
errada, para o timing não revelar quais e-mails existem.

Autorização por Gate e Policies — **nega por padrão**:

```python
Gate.define("update-post", lambda user, post: post.user_id == user.id)
Gate.authorize("update-post", user, post)   # levanta se negado
```

---

## Validação

```python
Validator(data, {
    "name":     ["required", "string", "max:255"],
    "email":    "required|email|unique:users,email",
    "age":      ["nullable", "integer", "between:18,120"],
    "password": ["required", "min:8", "confirmed"],
})
```

Regras: presença (`required`, `required_if`, `required_with`, `nullable`),
tipos (`string`, `integer`, `numeric`, `boolean`, `array`, `date`), formatos
(`email`, `url`, `uuid`, `alpha*`, `regex`), tamanho (`min`, `max`, `between`,
`size`), conjuntos (`in`, `not_in`, `same`, `different`, `confirmed`,
`accepted`) e banco (`unique`, `exists`).

Ou declarativo, com autorização junto:

```python
class StorePostRequest(FormRequest):
    def authorize(self):
        return self.user() is not None

    def rules(self):
        return {"title": ["required", "string", "max:255"]}

data = StorePostRequest(request).validated()   # levanta se falhar
```

---

## Cache, filas e eventos

```python
Cache.remember("stats", 300, lambda: expensive())   # array | file | redis
Queue.push(SendEmail(user_id=1))                    # sync | database
Event.dispatch(UserRegistered(user))
```

Jobs são serializados em **JSON**, nunca pickle, então um worker em outro
processo consegue reconstruí-los. Retry com backoff e `available_at` inclusos.

---

## Testes

```bash
python -m pytest                       # SQLite em memória (padrão)

# PostgreSQL real
$env:CODEPY_TEST_DB="pgsql"
$env:DB_HOST="127.0.0.1"; $env:DB_PORT="5499"
$env:DB_DATABASE="codepy_validation"
$env:DB_USERNAME="codepy"; $env:DB_PASSWORD="secretpassword"
python -m pytest

docker exec framework python -m pytest  # Python 3.11, a versão mínima
```

O `conftest.py` constrói o schema com o **migrator real**, então as migrations
são exercitadas a cada rodada em vez de dependerem de fixtures paralelas.

---

## Documentação

A documentação completa está em [`documentation/`](documentation/README.md):
instalação, configuração, container, rotas, controllers, views, validação,
migrations, ORM, segurança, sessões, cache, filas, resources, i18n, testes,
deploy e a referência do `craft`.

- [`CHANGELOG.md`](CHANGELOG.md) — o que mudou, em formato Keep a Changelog.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — como contribuir.
- [`SECURITY.md`](SECURITY.md) — política de segurança e checklist de produção.
- [`.agents/docs/backlog.md`](.agents/docs/backlog.md) — próximas fatias e
  decisões em aberto.

## Licença

[MIT](LICENSE) — © 2026 Antonio Santos &lt;snarthost@gmail.com&gt;
