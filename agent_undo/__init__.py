"""
Agent-Undo: Universal Transactional Rollback & Compensating Sagas for MCP Tools.
Supports Claude Opus 5.5, GPT-6 Astra, and Gemini 3.8 Flash.
"""

from .models import (
    TransactionStatus,
    ToolActionRecord,
    RollbackReport,
    SagaSession,
)
from .saga_engine import SagaEngine
from .mcp_wrapper import TransactionalMCPWrapper

__version__ = "1.0.0"
__all__ = [
    "TransactionStatus",
    "ToolActionRecord",
    "RollbackReport",
    "SagaSession",
    "SagaEngine",
    "TransactionalMCPWrapper",
]
