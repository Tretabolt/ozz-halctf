import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.core import OzzAgent, Observation, Plan
from agent.memory import Memory


class TestExecutionLearning(unittest.TestCase):
    def _make_agent(self):
        agent = object.__new__(OzzAgent)
        agent.memory = Memory(db_path=os.path.join(tempfile.gettempdir(), "ozz-test-learning.db"))
        agent.plan = Plan(objective="test", findings={}, credentials=[], flags_found=[])
        agent.run_metrics = {}
        agent.targets = ["target-01"]
        agent.current_target_idx = 0
        agent.history = []
        agent.action_effectiveness = {}
        return agent

    def test_recovery_action_is_selected_after_repeated_failures(self):
        agent = self._make_agent()
        agent._record_action_outcome("shell", False, "parse error")
        agent._record_action_outcome("shell", False, "parse error")
        recommendation = agent._choose_learning_guided_action(
            Observation(tool="shell", command="shell", output="parse error", success=False)
        )
        self.assertEqual(recommendation["action"], "quick_scan")


if __name__ == "__main__":
    unittest.main()
