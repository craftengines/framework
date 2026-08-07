# Resumo executivo — sessão 2026-08-07 (Craft Framework)

> Leia primeiro se estiver retomando o trabalho: este documento consolida o
> que mudou hoje. Detalhe linha a linha de cada mudança está no
> [`CHANGELOG.md`](../../data/CHANGELOG.md) (`data/`); decisões e achados
> específicos estão espalhados pelo resto deste `backlog.md` e no
> [`benchmark-2026-08-07.md`](benchmark-2026-08-07.md).

## O que entrou hoje, em ordem

### 1. Reorganização do workspace

O esqueleto da aplicação (`app/`, `services/`, `documentation/`, `tests/`
etc.) foi consolidado em `data/` — a raiz montada 1:1 no container Docker
(`build: .` / `volumes: .:/app` resolvem relativos a `data/`). Editar
qualquer arquivo ali reflete no container rodando imediatamente, sem
rebuild. Skill nova `.agents/skills/project/workspace-architecture/SKILL.md`
documenta o contrato para clonar isto e iniciar uma nova app sem recriar o
erro que motivou a reorganização.

### 2. Documentação e comentários 100% inglês

Auditoria completa de `documentation/*.md` e comentários de orientação em
`services/` contra o código real — achou e corrigiu 2 afirmações falsas
(SQLAlchemy no ORM, criptografia pós-quântica na sessão). 41 arquivos
ganharam o cabeçalho `Category/Relations/References` para orientar agentes
de IA. Regra codificada na skill `craft-framework-development`: 100% inglês
em `data/`, outro idioma só via camada de tradução.

### 3. Versionamento e release

Primeira release cortada: **`v3.11.0-r00001`**, tag git anotada. Regra
formalizada em `CONTRIBUTING.md`: o contador de release (`rNNNNN`) sempre
incrementa por 1, nunca reseta. `CHANGELOG.md` reaberto com `[Unreleased]`
no topo e regra obrigatória — toda mudança em código do framework precisa
de entrada no mesmo commit, não depois.

### 4. Plugin management + CRUD builder (fatias 3 e 4)

`PluginManager` nivelado ao `ModuleManager` — descoberta em disco,
persistência em banco, CLI (`plugin:list/enable/disable/sync`). CRUD builder
(`dev.py make crud <Entity> --fields "..."`) gera migration, model,
FormRequest, Resource, controller ligado de verdade ao ORM, **e** (desde a
correção do item 4 do benchmark) uma UI admin completa — lista paginada +
formulário de criar/editar — por padrão, sem flag extra.

### 5. Benchmark vs. mercado

Teste de carga real (stdlib puro, sem ferramenta externa) + 4 auditorias
especializadas (segurança, performance/escalabilidade, CI/CD/DX, UI/UX)
contra código real, comparadas contra Laravel/Django/Rails/Spring
Boot/ASP.NET Core/Node. 26 achados. Gráfico de calor salvo em
[`.claude/plans/benchmark-2026-08-07.html`](../../.claude/plans/benchmark-2026-08-07.html)
(abre offline) e publicado como Artifact.

**Achado mais importante**: throughput medido plano em ~30 req/s
independente da concorrência (1→100 clientes) — assinatura de processamento
totalmente serializado. `/docs` (rota mais pesada) quebrou com 74% de erro
em concorrência 100.

### 6. Correção dos achados críticos/altos do benchmark

22 dos 26 achados corrigidos em 4 frentes paralelas: segurança (CRUD builder
não tinha auth em rotas de escrita — API pública de exclusão por padrão;
mass assignment invertido; headers de segurança ausentes; `APP_KEY` vazio
degradava em silêncio), CI/DX (pipeline testava menos do que o próprio
`CONTRIBUTING.md` exigia), UI/UX (`/admin` não renderizava o template que já
existia; blog perdia o formulário em erro de validação).

**Deliberadamente não corrigido**: o teto de concorrência (item 4 acima).
Um agente tentou o pool de conexão e parou de propósito ao descobrir que a
conexão atual mistura estado de transação/schema de tenant — resolver
direito exige lifecycle de conexão por-requisição, não uma troca local.
Continua como o item de maior impacto pendente.

### 7. RBAC funcional + logins demo oficiais

`roles`/`permissions` já existiam como tabelas, mas ninguém as lia — hoje
`Gate.allows()` cai automaticamente no sistema de permissões, há middleware
`role:<slug>`/`permission:<slug>`, CLI completo, e uma UI admin mínima. Os 3
logins demo já seedados (`user@craft.local`, `tenant@craft.local`,
`admin@craft.local`, senha `craft`) viraram credencial oficial documentada —
o usuário `tenant` que não tinha papel nenhum ganhou o papel novo
`tenant-manager`, fechando a escada de 3 níveis. Credenciais também
aparecem na própria tela de `/login`, mas só quando `APP_DEBUG=true`.

Dois bugs reais de teste encontrados só ao rodar a suíte completa (não em
isolamento): um `TypeError` cru em vez de `KeyError` acionável no kernel, e
uma poluição de estado entre arquivos de teste (`test_framework.py`
quebrava o schema de `modules`/`translations` para quem rodasse depois).
Ambos corrigidos na origem.

## Estado atual

- **658/658 testes passando**, SQLite + PostgreSQL real + Python 3.11 do
  container. Cada arquivo também passa isolado.
- App validado ao vivo em `http://localhost:8300` — login com CSRF/captcha,
  headers de segurança, gates de `/admin`, `/admin/roles`, CRUD gerado.
- Nada foi enviado a um remoto — todo o histórico é local.

## O que falta, em ordem de impacto

1. **Concorrência real** (item 6 acima) — pool de conexão → offload de
   thread → `--workers`, nessa ordem, nunca ao contrário.
2. CRUD builder: reordenar linhas de campo, validação client-side antes do
   submit.
3. Ver o resto de `.agents/docs/backlog.md` para achados menores do
   benchmark ainda não triados em fatia própria.
