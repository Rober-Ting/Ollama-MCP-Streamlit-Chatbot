# Ollama MCP (Model Context Protocol)

Ollama MCP is a tool for connecting Ollama-based language models with external tools and services using the Model Context Protocol (MCP). This integration enables LLMs to interact with various systems like Git repositories, filesystems, Excel files, and other tool-enabled services through a flexible configuration system.

## Features

- Seamless integration between Ollama language models and MCP servers
- **Flexible configuration system** - Support multiple MCP servers via `config.json`
- **Multiple connection modes** - stdio, SSE, HTTP connections
- Support for Git operations through MCP Git server
- Support for filesystem operations through MCP Filesystem server
- Support for Excel operations through MCP Excel server
- Extensible tool management system
- Interactive command-line assistant interface
- Interactive Ollama model selection at startup from available local models
- **Configurable model storage** - Custom Ollama models directory

## Installation

1. Ensure you have Python 3.13+ installed
2. Clone this repository
3. Install dependencies:

```bash
# Create a virtual environment
uv add ruff check
# Activate the virtual environment
source .venv/bin/activate
# Install the package in development mode
uv pip install -e .
```

## Configuration

The application uses `config.json` to manage MCP server configurations. You can configure multiple servers with different connection modes:

```json
{
  "default_server_type": "git",
  "MCP_Servers": {
    "git": {
      "type": "uvx",
      "mode": "stdio",
      "connection": {
        "command": "uvx",
        "args": ["mcp-server-git"],
        "env": null
      }
    },
    "filesystem": {
      "type": "npx",
      "mode": "stdio",
      "connection": {
        "command": "npx",
        "args": ["@modelcontextprotocol/server-filesystem"],
        "env": null
      }
    },
    "excel": {
      "mode": "stdio",
      "connection": {
        "command": "npx",
        "args": ["--yes", "@negokaz/excel-mcp-server"],
        "env": {
          "EXCEL_MCP_PAGING_CELLS_LIMIT": "4000"
        }
      }
    }
  }
}
```

## Usage

### Ollama Model Selection

Before the main application starts, you will be prompted to select an Ollama model to use.

1.  **Prerequisites**:
    *   Ensure Ollama is installed and running.
    *   You must have at least one model pulled locally (e.g., via `ollama pull llama3.1:8b`). A list of models that support tool usage can be found on the [Ollama website](https://ollama.com/search?c=tools).

2.  **Startup Process**:
    *   The application will automatically detect and list all Ollama models available on your local machine.
    *   You will be prompted to type the name of the model you wish to use from the displayed list.
    *   If you enter an invalid model name, you will be prompted again until a valid selection is made.
    *   The chosen model will then be used by the agent for all subsequent operations.

### MCP Server Selection

After selecting a model, you can choose which MCP server to use:

1. **Available servers** are listed from your `config.json`
2. **Default server** is highlighted (configurable in `config.json`)
3. **Repository path** is only required for Git server

### Running the Assistant

```bash
uv run main.py
```

### To run tests
```bash
pytest -xvs tests/test_ollama_toolmanager.py
```

This will start an interactive CLI where you can ask the assistant to perform operations using the selected MCP server.

## Project Structure

```
ollama-mcp-client/
├── main.py                 # Main application entry point
├── ollama_agent.py         # Ollama agent for LLM interaction
├── ollama_toolmanager.py   # Tool management and execution
├── mcpclient_manager.py    # MCP client connection management
├── config.json            # MCP server configurations
├── .ollama/               # Local Ollama models directory
└── tests/                 # Test files
```

## Components

- **OllamaAgent** (`ollama_agent.py`): Orchestrates Ollama LLM and tool usage
- **OllamaToolManager** (`ollama_toolmanager.py`): Manages tool registrations and execution
- **MCPClientManager** (`mcpclient_manager.py`): Handles communication with MCP servers
- **Configuration System**: Flexible MCP server management via `config.json`

## Examples

### Using Git Server
```python
# The application will automatically use the git server configuration
# and prompt for repository path
async with MCPClientManager("git", repo_path) as client:
    tools = await client.get_available_tools()
    # Use tools for Git operations
```

### Using Filesystem Server
```python
# Connect to filesystem server
async with MCPClientManager("filesystem") as client:
    tools = await client.get_available_tools()
    # Use tools for filesystem operations
```

### Using Custom Server
```python
# Connect to custom SSE server
async with MCPClientManager("custom_server") as client:
    tools = await client.get_available_tools()
    # Use tools for custom operations
```

## Requirements

- Python 3.13+
- MCP 1.5.0+
- Ollama 0.4.7+
- Rich (for CLI interface)

## Customization

### Custom Ollama Models Directory
The application automatically sets up a local `.ollama/models` directory in your project folder, making it portable and self-contained.

### Adding New MCP Servers
1. Add server configuration to `config.json`
2. The application will automatically detect and list new servers
3. No code changes required for new server types

### Extending with Custom Tools
You can extend the system by:
1. Creating new tool wrappers
2. Registering them with the `OllamaToolManager`
3. Connecting to different MCP servers via configuration

