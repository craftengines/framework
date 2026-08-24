# Guia de Contribuição — Craft Framework

Obrigado por querer contribuir com o **Craft Framework**! Este documento orienta como configurar seu ambiente, propor melhorias, reportar bugs e enviar Pull Requests.

---

## 📋 Sumário

1. [Código de Conduta](#-código-de-conduta)
2. [Estrutura do Repositório](#-estrutura-do-repositório)
3. [Configuração do Ambiente Local](#-configuração-do-ambiente-local)
4. [Como Contribuir](#-como-contribuir)
   - [Reportando Bugs](#reportando-bugs)
   - [Sugerindo Melhorias](#sugerindo-melhorias)
   - [Enviando um Pull Request (PR)](#enviando-um-pull-request-pr)
5. [Padrões de Código e Commits](#-padrões-de-código-e-commits)
6. [Executando Testes](#-executando-testes)

---

## 📜 Código de Conduta

Ao participar deste projeto, você concorda em seguir o nosso [Código de Conduta](CODE_OF_CONDUCT.md), garantindo um ambiente respeitoso e acolhedor para todos.

---

## 📂 Estrutura do Repositório

```
craft-framework/
├── .agents/       # Documentações de arquitetura interna e especificações
├── .github/       # Workflows de CI/CD e templates de Issue/PR
└── data/          # Código da aplicação e do framework (montado no Docker)
    ├── app/       # Controladores, modelos e lógica da aplicação
    ├── bootstrap/ # Inicialização do Kernel
    ├── config/    # Configurações do framework
    ├── engine/    # Núcleo do Craft (ORM, Router, Auth, Security, etc.)
    ├── routes/    # Definição de rotas HTTP e WebSocket
    └── tests/     # Testes automatizados (pytest)
```

> **Atenção:** Toda a lógica do framework e da aplicação reside no diretório `data/`.

---

## 🛠 Configuração do Ambiente Local

### Pré-requisitos
- **Git**
- **Docker** e **Docker Compose**
- **Python 3.14+** (caso queira rodar fora do Docker)

### Passo a Passo

1. **Faça o Fork** do repositório no GitHub para sua conta.
2. **Clone** o seu fork localmente:
   ```bash
   git clone https://github.com/SEU_USUARIO/craft-framework.git
   cd craft-framework
   ```
3. **Configure as variáveis de ambiente**:
   ```bash
   cd data
   cp .env.example .env  # se houver, ou configure as chaves necessárias
   ```
4. **Inicie o ambiente com Docker Compose**:
   ```bash
   docker compose up -d --build
   ```
5. **Verifique se os serviços estão rodando**:
   ```bash
   docker compose ps
   ```

---

## 🚀 Como Contribuir

### Reportando Bugs
- Antes de abrir uma Issue, verifique se o problema já não foi relatado nas **Issues existentes**.
- Utilize o template de **Bug Report** incluindo passos para reprodução, versão do Python/Docker e mensagens de erro completas.

### Sugerindo Melhorias
- Abra uma Issue usando o template de **Feature Request**.
- Explique o caso de uso e como a melhoria beneficia o ecossistema do Craft Framework.

### Enviando um Pull Request (PR)

1. Crie uma nova branch a partir da `main`:
   ```bash
   git checkout -b feature/nome-da-sua-feature
   # ou
   git checkout -b fix/descricao-do-bug
   ```
2. Faça as alterações necessárias seguindo as boas práticas e padrões do projeto.
3. Adicione ou atualize os **testes** correspondentes em `data/tests/`.
4. Garanta que todos os testes passem:
   ```bash
   # Dentro do container Docker ou do diretório data/
   pytest
   ```
5. Faça o commit seguindo o padrão de **Conventional Commits**:
   ```bash
   git commit -m "feat(orm): add support for composite primary keys"
   ```
6. Envie a branch para o seu repositório remoto:
   ```bash
   git push origin feature/nome-da-sua-feature
   ```
7. Abra o **Pull Request** no GitHub apontando para a branch `main` do repositório original.
8. Preencha o checklist do template do Pull Request com clareza.

---

## 📝 Padrões de Código e Commits

### Padrão de Commits (Conventional Commits)
Utilizamos mensagens de commit estruturadas:
- `feat:` Nova funcionalidade
- `fix:` Correção de bug
- `docs:` Alterações na documentação
- `style:` Formatação de código sem alteração de lógica
- `refactor:` Refatoração de código
- `test:` Adição ou ajuste de testes
- `chore:` Manutenção, dependências ou tarefas auxiliares

*Exemplo:* `feat(security): implement ip rate limiter in firewall middleware`

### Guia de Estilo de Código
- Código formatado segundo **PEP 8**.
- Tipagem estática com **Type Hints** em novas funções e métodos.
- Mantenha a documentação (docstrings) atualizada.

---

## 🧪 Executando Testes

Para rodar a suíte completa de testes:

```bash
# Se estiver no host com ambiente configurado:
cd data
pytest

# Ou via Docker Compose:
docker compose exec app pytest
```

---

Dúvidas? Abra uma **Discussion** ou uma **Issue** no repositório!
