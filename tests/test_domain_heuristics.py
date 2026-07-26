import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.core import OzzAgent, Observation, Plan
from agent.memory import Memory


class TestDomainHeuristics(unittest.TestCase):
    def _make_agent(self):
        agent = object.__new__(OzzAgent)
        agent.memory = Memory(db_path=os.path.join(tempfile.gettempdir(), "ozz-test-domain.db"))
        agent.plan = Plan(objective="test", findings={}, credentials=[], flags_found=[])
        agent.run_metrics = {}
        return agent

    def test_prioritize_web_probe_when_http_service_is_found(self):
        agent = self._make_agent()
        obs = Observation(tool="nmap", command="nmap", output="80/tcp open http", success=True)
        recommendation = agent._recommend_next_action(obs)
        self.assertIn("curl", recommendation["action"])

    def test_prioritize_ssh_probe_when_ssh_service_is_found(self):
        agent = self._make_agent()
        obs = Observation(tool="nmap", command="nmap", output="22/tcp open ssh", success=True)
        recommendation = agent._recommend_next_action(obs)
        self.assertIn("ssh", recommendation["action"])


if __name__ == "__main__":
    unittest.main()
