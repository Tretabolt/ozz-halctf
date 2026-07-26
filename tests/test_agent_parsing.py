import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.core import OzzAgent, Observation, Plan, AgentState
from agent.memory import Memory


class TestAgentParsing(unittest.TestCase):
    def _make_agent(self):
        agent = object.__new__(OzzAgent)
        agent.memory = Memory(db_path=os.path.join(tempfile.gettempdir(), "ozz-test-parsing.db"))
        agent.plan = Plan(objective="test", findings={}, credentials=[], flags_found=[])
        agent.run_metrics = {}
        return agent

    def test_extract_services_from_nmap_output(self):
        agent = self._make_agent()
        obs = Observation(tool="nmap", command="nmap -sV", output="80/tcp open http\n22/tcp open ssh", success=True)

        agent._interpret_observation(obs)

        self.assertIn("80/tcp open http", agent.plan.findings["services"])
        self.assertIn("22/tcp open ssh", agent.plan.findings["services"])

    def test_extract_credentials_from_output(self):
        agent = self._make_agent()
        obs = Observation(tool="curl", command="curl", output="username=admin\npassword=s3cr3t", success=True)

        agent._interpret_observation(obs)

        self.assertEqual(agent.plan.credentials[0]["username"], "admin")
        self.assertEqual(agent.plan.credentials[0]["password"], "s3cr3t")

    def test_extract_vulnerabilities_from_output(self):
        agent = self._make_agent()
        obs = Observation(tool="nikto", command="nikto", output="Possible SQL injection detected via parameter id", success=True)

        agent._interpret_observation(obs)

        self.assertIn("sql injection", agent.plan.findings["vulnerabilities"])


if __name__ == "__main__":
    unittest.main()
