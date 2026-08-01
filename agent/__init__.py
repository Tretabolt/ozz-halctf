"""Ozz — HALctf Autonomous Pentesting Agent"""

from .core import OzzAgent
from .llm import LLM
from .memory import Memory
from .tools import ToolRegistry, Tool, ToolResult
from .scoreboard import ScoreboardClient
from .circuit_breaker import ResilienceManager
from .network_discovery import NetworkDiscovery

__version__ = "0.2.0"
__all__ = [
    "OzzAgent", "LLM", "Memory", "ToolRegistry", "Tool", "ToolResult",
    "ScoreboardClient", "ResilienceManager", "NetworkDiscovery",
]
