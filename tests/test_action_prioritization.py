import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.core import OzzAgent, Observation, Plan
from agent.memory import Memory


class TestActionPrioritization(unittest.TestCase):
    def _make_agent(self):
        agent = object.__new__(OzzAgent)
        agent.memory = Memory(db_path=os.path.join(tempfile.gettempdir(), "ozz-test-priority.db"))
        agent.plan = Plan(objective="test", findings={"services": ["80/tcp open http"], "vulnerabilities": ["sql injection"]}, credentials=[{"username": "admin", "password": "s3cr3t"}], flags_found=[])
        agent.run_metrics = {}
        return agent

    def test_priority_prefers_exploit_when_vulnerability_is_known(self):
        agent = self._make_agent()
        obs = Observation(tool="nikto", command="nikto", output="Possible SQL injection detected via parameter id", success=True)
        suggestion = agent._select_next_action(obs)
        self.assertIn("sqlmap", suggestion["action"])

    def test_priority_prefers_recon_when_no_findings_exist(self):
        agent = self._make_agent()
        agent.plan.findings = {}
        agent.plan.credentials = []
        obs = Observation(tool="nmap", command="nmap", output="Host is up", success=True)
        suggestion = agent._select_next_action(obs)
        self.assertIn("quick_scan", suggestion["action"])


if __name__ == "__main__":
    unittest.main()
