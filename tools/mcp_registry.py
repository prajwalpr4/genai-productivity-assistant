"""
MCP (Model Context Protocol) Tool Registry
===========================================
Provides a centralised, protocol-compliant catalogue of every tool
available to the multi-agent system.  Each tool is registered with a
domain tag (calendar / tasks / notes) so agents and the discovery API
can query what capabilities are available.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPToolRecord:
    """Metadata wrapper around a LangChain tool."""
    name: str
    domain: str
    description: str
    tool: Any  # The actual LangChain BaseTool instance


class MCPToolRegistry:
    """
    A lightweight registry inspired by the Model Context Protocol.
    Tools self-register on import, and the FastAPI /tools endpoint
    exposes them for discovery.
    """

    def __init__(self) -> None:
        self._records: dict[str, MCPToolRecord] = {}
        self._domains: dict[str, list[Any]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register(self, tool: Any, domain: str) -> None:
        """Register a LangChain tool under a domain."""
        record = MCPToolRecord(
            name=tool.name,
            domain=domain,
            description=tool.description,
            tool=tool,
        )
        self._records[tool.name] = record
        self._domains.setdefault(domain, []).append(tool)

    def register_many(self, tools: list[Any], domain: str) -> None:
        for t in tools:
            self.register(t, domain)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def get_tools_by_domain(self, domain: str) -> list[Any]:
        return self._domains.get(domain, [])

    def get_all_tools(self) -> list[Any]:
        return [r.tool for r in self._records.values()]

    def list_tools(self) -> list[dict]:
        """Return JSON-serialisable metadata for every registered tool."""
        return [
            {"name": r.name, "domain": r.domain, "description": r.description}
            for r in self._records.values()
        ]

    def __len__(self) -> int:
        return len(self._records)


# ── Global singleton ────────────────────────────────────────────────
registry = MCPToolRegistry()
