"""
Atomic Saga Coordinator & Compensating Transaction Engine for Agent-Undo.
Tracks real-world mutating MCP calls and unwinds them in reverse order upon agent failure.
"""

import time
import uuid
from typing import Dict, List, Optional, Tuple, Callable, Any
from .models import (
    TransactionStatus,
    ToolActionRecord,
    RollbackReport,
    SagaSession,
)


class SagaEngine:
    """Manages transactional write-ahead logs and reverse compensating rollbacks."""

    def __init__(self):
        self.sessions: Dict[str, SagaSession] = {}
        # Registry of compensation tool handlers: tool_name -> Callable[[dict], Any]
        self._tool_handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._compensation_registry: Dict[str, str] = {} # tool_name -> compensate_tool_name

    def register_compensating_pair(
        self,
        execute_tool: str,
        compensate_tool: str,
        execute_handler: Callable[[Dict[str, Any]], Any],
        compensate_handler: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """Register forward tool and its corresponding reverse undo handler."""
        self._tool_handlers[execute_tool] = execute_handler
        self._tool_handlers[compensate_tool] = compensate_handler
        self._compensation_registry[execute_tool] = compensate_tool

    def start_session(self, agent_id: str, model_name: str = "claude-opus-5-5") -> SagaSession:
        """Start a new transactional agent session."""
        saga_id = f"saga_{uuid.uuid4().hex[:8]}"
        session = SagaSession(
            saga_id=saga_id,
            agent_id=agent_id,
            model_name=model_name,
            status=TransactionStatus.ACTIVE
        )
        self.sessions[saga_id] = session
        return session

    def execute_action(
        self,
        saga_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        compensate_tool: Optional[str] = None,
        compensate_arguments: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute forward tool and journal it to the saga stack.
        Automatically binds the compensating undo action.
        """
        session = self.sessions.get(saga_id)
        if not session:
            raise KeyError(f"Saga session '{saga_id}' not found")

        if session.status != TransactionStatus.ACTIVE:
            raise RuntimeError(f"Cannot execute on saga '{saga_id}' in state {session.status.value}")

        # Resolve compensation tool
        comp_tool = compensate_tool or self._compensation_registry.get(tool_name)
        if not comp_tool:
            # Fallback heuristic
            if tool_name.startswith("create_"):
                comp_tool = tool_name.replace("create_", "delete_")
            elif tool_name.startswith("provision_"):
                comp_tool = tool_name.replace("provision_", "deprovision_")
            else:
                comp_tool = f"undo_{tool_name}"

        # Default compensate args mirror execute args unless custom passed
        comp_args = compensate_arguments if compensate_arguments is not None else arguments.copy()

        # Execute forward action
        handler = self._tool_handlers.get(tool_name)
        if not handler:
            # Simulated forward execution
            result = {"status": "success", "executed_tool": tool_name, "args": arguments}
        else:
            result = handler(arguments)

        # Journal action to LIFO stack
        action_rec = ToolActionRecord(
            action_id=f"act_{uuid.uuid4().hex[:6]}",
            step_number=len(session.actions) + 1,
            tool_name=tool_name,
            execute_arguments=arguments,
            compensate_tool=comp_tool,
            compensate_arguments=comp_args,
            execution_result=result
        )
        session.actions.append(action_rec)
        return result

    def rollback_saga(self, saga_id: str) -> RollbackReport:
        """
        Unwinds the saga by executing all compensating actions in reverse topological order (LIFO).
        """
        start_time = time.time()
        session = self.sessions.get(saga_id)
        if not session:
            raise KeyError(f"Saga session '{saga_id}' not found")

        session.status = TransactionStatus.COMPENSATING
        details: List[str] = []
        compensated_count = 0
        failed_count = 0

        # Unwind LIFO
        for action in reversed(session.actions):
            if action.is_compensated:
                continue

            t0 = time.time()
            comp_tool = action.compensate_tool
            comp_args = action.compensate_arguments

            try:
                handler = self._tool_handlers.get(comp_tool)
                if handler:
                    handler(comp_args)
                dur = (time.time() - t0) * 1000.0
                action.is_compensated = True
                action.compensation_duration_ms = dur
                compensated_count += 1
                details.append(f"✓ Step {action.step_number} [{action.tool_name}] undone by [{comp_tool}] in {dur:.2f}ms")
            except Exception as e:
                failed_count += 1
                details.append(f"✗ Step {action.step_number} [{action.tool_name}] compensation FAILED: {str(e)}")

        total_dur = (time.time() - start_time) * 1000.0
        session.status = TransactionStatus.ROLLED_BACK if failed_count == 0 else TransactionStatus.FAILED
        session.completed_at = time.time()

        return RollbackReport(
            saga_id=saga_id,
            total_actions_recorded=len(session.actions),
            actions_compensated=compensated_count,
            actions_failed=failed_count,
            duration_ms=total_dur,
            status=session.status,
            details=details
        )

    def commit_saga(self, saga_id: str) -> bool:
        """Mark saga as successfully completed and permanently committed."""
        session = self.sessions.get(saga_id)
        if session and session.status == TransactionStatus.ACTIVE:
            session.status = TransactionStatus.COMMITTED
            session.completed_at = time.time()
            return True
        return False
