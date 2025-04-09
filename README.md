# MCP

Configure the MCP server to view company information and stock prices using the Claude<br><br>

claude_desktop_config.json<br>
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
