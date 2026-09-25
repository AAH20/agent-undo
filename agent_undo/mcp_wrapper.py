"""
MCP Server Decorator & Transactional Interceptor for Agent-Undo.
Enriches Model Context Protocol tool schemas with declarative compensation metadata.
"""

from typing import Dict, List, Optional, Callable, Any
from .saga_engine import SagaEngine


class TransactionalMCPWrapper:
    """Wraps MCP tool registries with automatic write-ahead logging and compensation hooks."""

    def __init__(self, saga_engine: SagaEngine):
        self.engine = saga_engine
        self.registered_tools: Dict[str, Dict[str, Any]] = {}

    def register_transactional_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        execute_handler: Callable[[Dict[str, Any]], Any],
        compensate_tool_name: str,
        compensate_handler: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """Register forward MCP tool and bind its compensating undo handler."""
        self.registered_tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
            "compensate_tool": compensate_tool_name
        }
        self.engine.register_compensating_pair(
            name,
            compensate_tool_name,
            execute_handler,
            compensate_handler
        )

    def export_mcp_tools(self) -> List[Dict[str, Any]]:
        """Export standardized MCP tool definitions for Claude Opus 5.5 and GPT-6 Astra."""
        tools = []
        for name, meta in self.registered_tools.items():
            tools.append({
                "name": name,
                "description": f"{meta['description']} (Transactional: undoable via {meta['compensate_tool']})",
                "inputSchema": meta["inputSchema"]
            })
        return tools
