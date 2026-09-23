"""
Laya Permission & Safety Gate
Categorizes actions into GREEN, YELLOW, and RED tiers.
Supports session approval and multi-turn confirmation workflows.
"""

from enum import Enum
from typing import Dict, Set, Optional, Tuple

from laya.config import GREEN_ACTIONS, YELLOW_ACTIONS, RED_ACTIONS


class PermissionTier(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class PermissionGate:
    _instance: Optional["PermissionGate"] = None

    def __init__(self):
        self.approved_actions: Set[str] = set()
        self.pending_action: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "PermissionGate":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_tier(self, action: str) -> PermissionTier:
        act = action.lower()
        if act in RED_ACTIONS or "shutdown" in act or "format" in act or "diskpart" in act:
            return PermissionTier.RED
        if act in YELLOW_ACTIONS or "email" in act or "whatsapp" in act:
            return PermissionTier.YELLOW
        return PermissionTier.GREEN

    def approve_action(self, action: str):
        """Approve an action for the session."""
        self.approved_actions.add(action.lower())
        self.pending_action = None

    def approve_pending(self) -> Optional[str]:
        """Approve whatever action was currently pending confirmation."""
        act = self.pending_action
        if act:
            self.approved_actions.add(act)
            self.pending_action = None
        return act

    def check(self, action: str, is_confirmed: bool = False, has_params: bool = False) -> Tuple[bool, str]:
        """
        Verify if action is permitted to execute.
        Returns: (allowed: bool, prompt_or_reason: str)
        """
        act = action.lower()
        tier = self.get_tier(act)

        if tier == PermissionTier.GREEN:
            return True, "Auto-approved."

        # If already approved in this session or explicitly confirmed
        if act in self.approved_actions or is_confirmed:
            return True, f"Approved action '{act}'."

        if tier == PermissionTier.YELLOW:
            # If user explicitly provided the complete payload (contact & message) in the instruction, auto-approve!
            if has_params:
                self.approved_actions.add(act)
                return True, f"Auto-approved explicit user command '{act}'."

            self.pending_action = act
            return False, f"Action '{act}' requires confirmation. Say 'yes' or 'proceed' to execute."

        if tier == PermissionTier.RED:
            self.pending_action = act
            return False, f"CRITICAL: Action '{act}' is a Red-tier destructive operation. Explicit repeat-back confirmation required."


def get_permission_gate() -> PermissionGate:
    return PermissionGate.get_instance()
