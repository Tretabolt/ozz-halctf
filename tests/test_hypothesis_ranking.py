import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.core import OzzAgent, Observation, Plan
from agent.memory import Memory


class TestHypothesisRanking(unittest.TestCase):
    def _make_agent(self):
        agent = object.__new__(OzzAgent)
        agent.memory = Memory(db_path=os.path.join(tempfile.gettempdir(), "ozz-test-hypothesis.db"))
        agent.plan = Plan(objective="test", findings={"services": ["80/tcp open http"], "vulnerabilities": ["sql injection"]}, credentials=[{"username": "admin", "password": "s3cr3t"}], flags_found=[])
        agent.run_metrics = {}
        agent.targets = ["target-01"]
        agent.current_target_idx = 0
        agent.history = []
        return agent

    def test_builds_hypotheses_and_ranks_them(self):
        agent = self._make_agent()
        obs = Observation(tool="nikto", command="nikto", output="Possible SQL injection detected via parameter id", success=True)
        hypotheses = agent._build_hypotheses(obs)
        self.assertGreaterEqual(len(hypotheses), 2)
        self.assertEqual(hypotheses[0]["priority"], "high")
        self.assertIn("sql injection", hypotheses[0]["hypothesis"])


if __name__ == "__main__":
    unittest.main()
