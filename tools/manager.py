"""Tool manager.

Claude never executes anything directly: it emits tool requests, the Agent SDK
routes them to this in-process MCP server, results go back to Claude.

Collects tools from the tools/ package and from enabled plugins/.
"""

from claude_agent_sdk import create_sdk_mcp_server

from plugins.loader import load_plugin_tools
from tools import alarms, browser, desktop, filesystem, screen, system

SERVER_NAME = "cortana"


class ToolManager:
    def __init__(self, plugins_enabled: bool = True):
        self.tools = [
            *desktop.TOOLS,
            *filesystem.TOOLS,
            *browser.TOOLS,
            *screen.TOOLS,
            *system.TOOLS,
            *alarms.TOOLS,
        ]
        if plugins_enabled:
            self.tools.extend(load_plugin_tools())
        self._server = create_sdk_mcp_server(
            name=SERVER_NAME, version="1.0.0", tools=self.tools
        )

    def mcp_servers(self) -> dict:
        return {SERVER_NAME: self._server}

    def allowed_tools(self) -> list[str]:
        return [f"mcp__{SERVER_NAME}__{t.name}" for t in self.tools]
