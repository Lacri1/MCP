# MCP: StocksMCPServer
This project configures the MCP server to view company information and stock prices using Claude.

## Configuration

The MCP server is defined in claude_desktop_config.json as follows:
```json
{
  "mcpServers": {
    "StocksMCPServer": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\user\\PycharmProjects\\mcp", #your project directory
        "run",
        "--with",
        "mcp",
        "mcp",
        "run",
        "main.py"
      ]
    }
  }
}
```
Make sure to update the "directory" field to match your project path if it’s different.

## Development Mode
You can also try it out interactively using MCP Inspector:

```bash
mcp dev main.py
```
