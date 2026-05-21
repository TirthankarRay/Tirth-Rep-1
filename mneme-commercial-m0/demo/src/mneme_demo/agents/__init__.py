"""Six simulated proposer agent profiles."""

from .diligent import DiligentAgent
from .confident_wrong import ConfidentWrongAgent
from .sloppy import SloppyAgent
from .aggressive import AggressiveAgent
from .adversarial import AdversarialAgent
from .stale import StaleAgent
from .base import AgentProposal


PROFILE_WEIGHTS = [
    (DiligentAgent,        0.30),
    (ConfidentWrongAgent,  0.20),
    (SloppyAgent,          0.20),
    (AggressiveAgent,      0.15),
    (AdversarialAgent,     0.10),
    (StaleAgent,           0.05),
]

__all__ = [
    "DiligentAgent", "ConfidentWrongAgent", "SloppyAgent", "AggressiveAgent",
    "AdversarialAgent", "StaleAgent", "PROFILE_WEIGHTS", "AgentProposal",
]
