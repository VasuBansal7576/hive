"""
SDR LinkedIn Monitor Agent — Use Case #58.

Monitors LinkedIn for 'I'm hiring' and 'Just started a new role' posts from
VP of Engineering and CTO titles at Series B+ companies. Finds corporate emails,
drafts personalized cold emails, and queues up to 50 per day for SDR review.
"""

from .agent import SdrLinkedinMonitorAgent, default_agent, goal, nodes, edges
from .config import RuntimeConfig, AgentMetadata, default_config, metadata

__version__ = "1.0.0"

__all__ = [
    "SdrLinkedinMonitorAgent",
    "default_agent",
    "goal",
    "nodes",
    "edges",
    "RuntimeConfig",
    "AgentMetadata",
    "default_config",
    "metadata",
]
