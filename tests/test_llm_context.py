import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.core import OzzAgent, Observation, Plan, AgentState
from agent.memory import Memory


class TestLLMContext(unittest.TestCase):
    def _make_agent(self):
        agent = object.__new__(OzzAgent)
        agent.memory = Memory(db_path=os.path.join(tempfile.gettempdir(), "ozz-test-llm-context.db"))
        agent.plan = Plan(objective="test", findings={"services": ["80/tcp open http"], "vulnerabilities": ["sql injection"]}, credentials=[{"username": "admin", "password": "s3cr3t"}], flags_found=[])
        agent.run_metrics = {}
        agent.targets = ["target-01"]
        agent.current_target_idx = 0
        agent.history = []
        agent.tools = None
        return agent

    def test_context_includes_structured_findings(self):
        agent = self._make_agent()
        context = agent._build_context()
        self.assertIn("sql injection", context)
        self.assertIn("80/tcp open http", context)
        self.assertIn("admin", context)

    def test_context_mentions_current_phase(self):
        agent = self._make_agent()
        agent.plan.state = AgentState.RECON
        context = agent._build_context()
        self.assertIn("CURRENT PHASE", context)


if __name__ == "__main__":
    unittest.main()
