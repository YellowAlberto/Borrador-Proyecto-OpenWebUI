---
title: Agente Futuro - Introducción
theme: black
separator: '^---$'
verticalSeparator: '^--$'
revealOptions:
  margin: 0.04
  minScale: 0.4
  maxScale: 1.6
  transition: slide
  slideNumber: 'c/t'
---

<style>
.reveal section {
  text-align: left;
}
.reveal section h1,
.reveal section h2,
.reveal section h3,
.reveal section h4 {
  text-align: center;
}
.reveal section h5 {
  text-align: right;
}
</style>

## Ejecución y depuración del herramientas con FastMCP
* Ejecucion de herramientas MCP server.
* Depuracion de herramientas MCP server.
* Ejecucion de herramientas a traves de MCPO.
* Autenticación bearer token MCPO.

--

### 1. Requisitos previos
- Extensión `ms-python.python` (incluye `debugpy`).
- Archivo `src/examples/fastmcp_random.py` con el tool y `mcp.run(...)`.
- VS Code devcontainer abierto en `/workspaces/ai-solver`.

--

### 2. Configuraciones de VS Code
` .vscode/launch.json` expone tres entradas relevantes:

1. **MCPO Proxy (FastMCP Random)**  
   Ejecuta el servidor (stdio) y conecta en modo Open API proxy.
2. **MCP (FastMCP Random + breakpoints)**  
   Ejecuta el servidor (http) y conecta en modo MCP.

--

### 4. Depuración MCP (HTTP directo)
Cambia `mcp.run(...)` para usar el transporte HTTP integrado:
```python
mcp.run(
    transport="http",
    host="0.0.0.0",
    port=8000,
    path="/mcp",
)
```

--

### 5. Conectando con OpenWeb UI
Icono Usuario > Admin Panel > Settings > External Tools > Añadir herramienta > Type > MCP
- Open WebUI debe referenciar `http://ai-solver:8000/mcp` (están en la misma red Docker).
- No auth required

--

### 6. Conectando con Open API proxy con autenticacion

- Cambia a modo stdio.
- Define el bearer token
- Arranca MCP en modo proxy MCPO
- Icono Usuario > Admin Panel > Settings > External Tools > Añadir herramienta > Type > Open API
- Bearer token
