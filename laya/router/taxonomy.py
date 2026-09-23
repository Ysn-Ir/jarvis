"""
Laya Execution Path Taxonomy and Decision Dataclasses
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any


class ExecutionPath(str, Enum):
    FAST_PATH = "fast_path"
    REASONING_PATH = "reasoning_path"
    VISION_FALLBACK = "vision_fallback"
    CLARIFY = "clarify"
    BLOCKED_SAFETY = "blocked_safety"


@dataclass
class RouteDecision:
    path: ExecutionPath
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    safety_tier: str = "GREEN"  # "GREEN", "YELLOW", "RED"
    confidence: float = 1.0
    reasoning: str = ""
    clarification_prompt: str = ""
