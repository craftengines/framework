# AI Agents & Model Context Protocol (MCP)

Craft Engine provides first-class support for AI Agents and the standard **Model Context Protocol (MCP)**, allowing external AI coding assistants, autonomous agents, and IDEs to discover and invoke application tools securely.

## 🛠️ Defining Agent Tools (`AgentTool`)

Create declarative, RBAC-guarded tools by subclassing `AgentTool`:

```python
# app/Tools/SearchArticlesTool.py
from craft.agents.tool import AgentTool
from app.Models.Article import Article

class SearchArticlesTool(AgentTool):
    name = "search_articles"
    description = "Search published articles by keyword or category."
    parameters = {
        "query": {"type": "string"},
        "limit": {"type": "integer"},
    }
    required = ["query"]
    required_permissions = ["read-articles"]

    def execute(self, query: str, limit: int = 5) -> list:
        return Article.where("title", "LIKE", f"%{query}%") \
            .limit(limit) \
            .get() \
            .to_dict()
```

---

## 🔌 Registering with the MCP Server

```python
from craft.facades import Agent, MCP

Agent.register_tool(SearchArticlesTool())

# Handle standard MCP JSON-RPC requests (e.g. from /api/mcp endpoint)
response = MCP.handle_mcp({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "search_articles",
        "arguments": {"query": "python"},
    },
}, user=request.user)
```
