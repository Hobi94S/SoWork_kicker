"""SoWork Kicker: verificação de presença e desconexão orientada por respostas."""

from .config import SoWorkKickerConfig
from .engine import VerificationEngine
from .models import MessageEvent, VerificationResult, VerificationStatus

__all__ = [
    "SoWorkKickerConfig",
    "VerificationEngine",
    "MessageEvent",
    "VerificationResult",
    "VerificationStatus",
]
