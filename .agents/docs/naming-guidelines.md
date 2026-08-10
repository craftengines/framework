# Craft — Naming Guidelines

Versão: 2026-08
Autor: Antonio Santos

> Documento oficial de referência. Em caso de divergência com
> [`trademark_safe_architecture.md`](trademark_safe_architecture.md), este
> prevalece — ver a seção "Pendências" ao final.

## 1. Objetivo

Definir claramente quais termos podem ser usados em um framework Python inspirado
no Laravel, garantindo segurança jurídica e evitando conflitos com marcas
registradas da Laravel LLC.

## 2. Princípio Geral

Nomes **não podem ser idênticos** nem **confundíveis** com marcas registradas da
Laravel LLC. Nomes **podem ser inspirados**, desde que sejam **originais,
modificados ou genéricos**.

Laravel possui marcas registradas para: Artisan, Eloquent, Blade, Illuminate,
Horizon, Nova, Spark, Jetstream, Sail, Valet.

Esses nomes **não devem ser usados**.

## 3. Termos Permitidos (Seguros)

| Conceito | Laravel | Craft | Onde vive |
|---|---|---|---|
| CLI / Console | Artisan | `dev.py` | `engine/cli` |
| ORM | Eloquent | Craft ORM | `craft.orm` |
| Template engine | Blade | Forge | `craft.view` |
| Container / IoC | `Illuminate\Container` | — | `craft.container` |
| Facades | Facades | — | `craft.facades` |
| Validação | FormRequest | — | `craft.validation` |
| Autorização | Gate / Policies | — | `craft.auth` |
| Migrations / Schema | Migrations | — | `craft.migrations` |

"Facade", "FormRequest", "Gate", "Policy", "Migration" e "Schema" são termos
correntes da engenharia de software, não marcas.

## 4. Termos Proibidos (Marcas Registradas)

Artisan · Eloquent · Blade · Illuminate · Horizon · Nova · Spark · Jetstream ·
Sail · Valet

Evitar também variações confundíveis: Artisane, Eloquente, Blader, Illuminated.

## 5. Regras Gerais de Segurança

1. Sempre usar nomes **originais** ou **genéricos**.
2. Nunca usar nomes **idênticos** aos da Laravel LLC.
3. Nunca usar nomes que causem **confusão fonética ou visual**.
4. Nomes inspirados devem ser **claramente diferenciados**.
5. Não copiar comportamento proprietário; apenas conceitos públicos.

## 6. Neutralidade: sem comparação com terceiros

**O projeto não cita nenhum framework de terceiros — em lugar nenhum.** Nem no
código, nem na documentação, nem na landing page, e nem como uso nominativo em
tabelas de comparação.

O uso nominativo é juridicamente defensável, mas amarra a identidade do Craft à
marca de outro. O framework se descreve pelo que faz:

> "A batteries-included Python web framework built on Starlette"

e não pelo que se parece.

Removido em 2026-08:

- Seção "Laravel ↔ Craft Equivalence" da landing page.
- Tabela "Equivalências com o Laravel" do `README.md`.
- Tabela "Coming from Laravel" de `documentation/README.md`.
- Toda menção em docstrings, comentários, descrição do pacote e keywords.

As únicas exceções são este documento e
[`trademark_safe_architecture.md`](trademark_safe_architecture.md), que tratam
justamente de política de marcas e precisam nomeá-las para discuti-las.

Verificação — deve retornar zero fora dos dois documentos acima:

```powershell
Select-String -Path (Get-ChildItem . -Recurse -Include *.py,*.md,*.toml,*.css,*.js -File |
  Where-Object { $_.FullName -notmatch '\.git\\|__pycache__|naming-guidelines|trademark_safe' }) `
  -Pattern "\b(laravel|artisan|eloquent|blade)\b" -CaseSensitive:$false
```

## 7. Estado da implementação

Aplicado em 2026-08:

- Extensão dos templates: `.blade.py` → **`.forge.py`** (14 arquivos).
- `BladeLoader` → **`DirectiveLoader`**.
- "Blade directives" → **"Forge directives"** em código, docstrings e docs.
- `CRAFT_DESIGN.md`, notas em `.agents/` e a documentação foram varridos.

Verificação:

```powershell
Select-String -Path (Get-ChildItem . -Recurse -Include *.py,*.md -File |
  Where-Object { $_.FullName -notmatch '\.git\\|__pycache__' }) -Pattern "blade" -CaseSensitive:$false
```

Só devem aparecer: este documento, `trademark_safe_architecture.md` e as três
tabelas de comparação.

## 8. Pendências

**"Forge" é o nome de um produto comercial da Laravel LLC** — o
[Laravel Forge](https://forge.laravel.com), serviço de provisionamento de
servidores. A lista da seção 4 não o inclui, mas o documento interno
`trademark_safe_architecture.md` (anterior a este) já o classificava como nome a
evitar e propunha **Loom** no lugar.

Os dois documentos divergem nesse ponto e a decisão está em aberto. O contexto
de uso é diferente — Laravel Forge é infraestrutura, Craft Forge é motor de
template — o que reduz o risco de confusão, mas não o elimina.

Isto não é aconselhamento jurídico. Se a decisão for trocar, o custo hoje é
baixo: o nome está concentrado em `engine/view/forge.py`, na extensão
`.forge.py` e nas menções em documentação.
