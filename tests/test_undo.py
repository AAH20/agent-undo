"""
Comprehensive Unit Test Suite for Agent-Undo.
"""

import unittest
from agent_undo.models import TransactionStatus
from agent_undo.saga_engine import SagaEngine
from agent_undo.mcp_wrapper import TransactionalMCPWrapper


class TestAgentUndo(unittest.TestCase):

    def setUp(self):
        self.engine = SagaEngine()
        self.state_db = {}

        # Register forward & backward handlers
        self.engine.register_compensating_pair(
            "insert_item", "delete_item",
            execute_handler=lambda args: self.state_db.update({args["id"]: args["val"]}),
            compensate_handler=lambda args: self.state_db.pop(args["id"], None)
        )

    def test_saga_commit_lifecycle(self):
        """Test happy path: actions execute and commit."""
        session = self.engine.start_session("agent_1")
        self.engine.execute_action(session.saga_id, "insert_item", {"id": "k1", "val": "v1"})
        self.assertEqual(self.state_db.get("k1"), "v1")

        committed = self.engine.commit_saga(session.saga_id)
        self.assertTrue(committed)
        self.assertEqual(session.status, TransactionStatus.COMMITTED)

    def test_saga_rollback_lifo_execution(self):
        """Test failure scenario: rolling back unwinds actions in reverse order."""
        session = self.engine.start_session("agent_2")
        self.engine.execute_action(session.saga_id, "insert_item", {"id": "item_1", "val": 100})
        self.engine.execute_action(session.saga_id, "insert_item", {"id": "item_2", "val": 200})
        self.assertEqual(len(self.state_db), 2)

        # Trigger rollback
        report = self.engine.rollback_saga(session.saga_id)
        self.assertEqual(report.status, TransactionStatus.ROLLED_BACK)
        self.assertEqual(report.actions_compensated, 2)
        # Database should now be empty
        self.assertEqual(len(self.state_db), 0)

    def test_mcp_wrapper_tool_export(self):
        """Test wrapping MCP tools with transactional metadata."""
        wrapper = TransactionalMCPWrapper(self.engine)
        wrapper.register_transactional_tool(
            name="create_bucket",
            description="Create cloud storage bucket",
            input_schema={"type": "object"},
            execute_handler=lambda args: True,
            compensate_tool_name="delete_bucket",
            compensate_handler=lambda args: True
        )

        tools = wrapper.export_mcp_tools()
        self.assertEqual(len(tools), 1)
        self.assertIn("Transactional: undoable via delete_bucket", tools[0]["description"])


if __name__ == "__main__":
    unittest.main()
