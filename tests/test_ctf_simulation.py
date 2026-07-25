"""
Suíte TDD de Validação E2E da Simulação CTF (Operation Blackout)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.ctf_simulation_operation_blackout import run_ctf_simulation


class TestCtfSimulationE2E(unittest.TestCase):
    """Valida a execução completa end-to-end do estudo de caso de CTF."""

    def test_run_ctf_simulation_executes_all_stages(self):
        """A simulação E2E deve completar as 7 fases com sucesso."""
        res = run_ctf_simulation()
        self.assertEqual(res["flags_captured"], 1)
        self.assertEqual(res["tournaments_executed"], 4)
        self.assertEqual(res["pwn_strategy"], "ROP_FIXED_BINARY_BASE")
        self.assertTrue(len(res["tau_hash"]) > 0)


if __name__ == "__main__":
    unittest.main()
