import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.core import OzzAgent, Observation, Plan
from agent.memory import Memory


class TestCrossRunMemory(unittest.TestCase):
    def _make_agent(self):
        agent = object.__new__(OzzAgent)
        agent.memory = Memory(db_path=os.path.join(tempfile.gettempdir(), "ozz-test-cross-run.db"))
        agent.plan = Plan(objective="test", findings={}, credentials=[], flags_found=[])
        agent.run_metrics = {}
        agent.targets = ["target-01"]
        agent.current_target_idx = 0
        agent.history = []
        agent.action_effectiveness = {}
        return agent

    def test_reuses_successful_actions_across_runs(self):
        agent = self._make_agent()
        agent.memory.store_run_metrics({"run_id": "run-1", "tool_failures": 0, "flags_found": 1}, run_id="run-1")
        agent.memory.store_run_metrics({"run_id": "run-2", "tool_failures": 3, "flags_found": 0}, run_id="run-2")

        prior = agent._load_prior_run_insights()
        self.assertIn("run-1", prior["best_runs"])
        self.assertEqual(prior["best_runs"]["run-1"]["flags_found"], 1)

    def test_build_context_includes_exploitdb_references_for_known_targets(self):
        agent = self._make_agent()
        agent.plan.findings["services"] = ["80/tcp open http"]
        agent.plan.findings["vulnerabilities"] = ["sql injection"]

        context = agent._build_context()

        self.assertIn("Exploit-DB", context)
        self.assertIn("https://www.exploit-db.com", context)
        self.assertIn("sql injection", context.lower())

    def test_build_context_includes_service_specific_strategy_guidance(self):
        agent = self._make_agent()
        agent.plan.findings["services"] = ["80/tcp open http"]
        agent.plan.findings["vulnerabilities"] = ["sql injection"]
        agent.memory.store_strategy_evidence(
            target="target-01",
            service="http",
            vulnerability="sql injection",
            action="sqlmap",
            reference="https://www.exploit-db.com",
            confidence=0.91,
            outcome="success",
        )

        context = agent._build_context()

        self.assertIn("service-specific strategy", context.lower())
        self.assertIn("sqlmap", context.lower())
        self.assertIn("https://www.exploit-db.com", context)


if __name__ == "__main__":
    unittest.main()
