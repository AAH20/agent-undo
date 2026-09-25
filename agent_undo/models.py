"""
Data models and transaction schemas for Agent-Undo.
Universal Transactional Rollback & Compensating Sagas for Model Context Protocol (MCP) Tools.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import time


class TransactionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMMITTED = "COMMITTED"
    COMPENSATING = "COMPENSATING"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


@dataclass
class ToolActionRecord:
    action_id: str
    step_number: int
    tool_name: str
    execute_arguments: Dict[str, Any]
    compensate_tool: str
    compensate_arguments: Dict[str, Any]
    executed_at: float = field(default_factory=time.time)
    execution_result: Optional[Any] = None
    is_compensated: bool = False
    compensation_duration_ms: float = 0.0


@dataclass
class RollbackReport:
    saga_id: str
    total_actions_recorded: int
    actions_compensated: int
    actions_failed: int
    duration_ms: float = 0.0
    status: TransactionStatus = TransactionStatus.ROLLED_BACK
    details: List[str] = field(default_factory=list)


@dataclass
class SagaSession:
    saga_id: str
    agent_id: str
    model_name: str              # e.g. "claude-opus-5-5", "gpt-6-astra"
    status: TransactionStatus = TransactionStatus.ACTIVE
    actions: List[ToolActionRecord] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
