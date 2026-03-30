"""Runtime configuration for SDR LinkedIn Monitor Agent."""

from dataclasses import dataclass
from framework.config import RuntimeConfig

default_config: RuntimeConfig = RuntimeConfig()


@dataclass
class AgentMetadata:
    """Metadata for the SDR LinkedIn Monitor Agent."""

    name: str = "SDR LinkedIn Monitor"
    version: str = "1.0.0"
    description: str = (
        "Monitors LinkedIn 24/7 for 'I'm hiring' and 'Just started a new role' posts "
        "from VP of Engineering and CTO titles at Series B+ companies, looks up verified "
        "corporate emails, and drafts highly personalized cold emails — queuing up to 50 "
        "per day."
    )
    intro_message: str = (
        "Hi! I'm your SDR LinkedIn Monitor. I'll scan LinkedIn for job-change and "
        "hiring signals from senior engineering leaders at Series B+ companies, find "
        "their corporate emails, and draft personalized cold emails for you to review. "
        "Let's set up your target criteria first."
    )


metadata: AgentMetadata = AgentMetadata()
