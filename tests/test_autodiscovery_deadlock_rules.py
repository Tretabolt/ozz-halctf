"""
Suíte TDD de Auto-Discovery, Prevenção de Deadlocks e Regras de Domínio (Portão 5 - RED)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAutoDiscovery(unittest.TestCase):
    """Valida o carregamento dinâmico de solvers via pkgutil sem imports manuais"""

    def test_pkgutil_autodiscovery_registers_solvers(self):
        """DomainSolverRegistry deve descobrir e registrar solvers em agent.domains automaticamente"""
        from agent.domains.registry import DomainSolverRegistry
        
        # Reseta o registro para testar a descoberta pura
        DomainSolverRegistry._solvers.clear()
        self.assertNotIn("pwn", DomainSolverRegistry._solvers)
        
        # Executa auto-descoberta
        DomainSolverRegistry.discover_solvers()
        self.assertTrue(DomainSolverRegistry.has_solver("pwn"))
        self.assertTrue(DomainSolverRegistry.has_solver("web"))
        self.assertTrue(DomainSolverRegistry.has_solver("forensics"))


class TestDeadlockAndTimeoutPrevention(unittest.TestCase):
    """Valida prevenção de deadlock e controle de exceções de infraestrutura"""

    def test_process_executor_timeout_kills_process(self):
        """SafeProcessExecutor deve matar processos em loop infinito via SIGKILL e retornar resultado gracioso"""
        from agent.infra.executor import SafeProcessExecutor
        from agent.dtos.domain_dtos import CommandSpec

        executor = SafeProcessExecutor()
        # Comando Python que entra em loop infinito
        infinite_loop_spec = CommandSpec(
            binary=sys.executable,
            args=["-c", "import time\nwhile True: time.sleep(0.1)"],
            timeout=0.5  # Timeout curto de 500ms
        )
        res = executor.execute(infinite_loop_spec)
        self.assertFalse(res.success)
        self.assertIn("EXECUTION_TIMEOUT_KILLED", res.error)
        self.assertEqual(res.exit_code, -9)

    def test_missing_binary_graceful_handling(self):
        """SafeProcessExecutor deve capturar FileNotFoundError para binários inexistentes sem estourar exceção"""
        from agent.infra.executor import SafeProcessExecutor
        from agent.dtos.domain_dtos import CommandSpec

        executor = SafeProcessExecutor()
        missing_bin_spec = CommandSpec(binary="non_existent_binary_xyz_123", args=[])
        res = executor.execute(missing_bin_spec)
        self.assertFalse(res.success)
        self.assertIn("BINARY_NOT_FOUND", res.error)


class TestDomainTacticalDecisionEngine(unittest.TestCase):
    """Valida regras de negócio puras de tomada de decisão tática no PwnRevDomainSolver"""

    def test_evaluate_tactical_strategy_rules(self):
        """PwnRevDomainSolver deve decidir a estratégia de exploração ideal com base nos controles de segurança"""
        from agent.domains.pwn_rev import PwnRevDomainSolver
        from agent.dtos.domain_dtos import TacticalStrategy

        solver = PwnRevDomainSolver()

        # Cenário 1: Sem NX -> Injection de Shellcode
        strat1 = solver.evaluate_tactical_strategy({"NX": False, "Canary": False, "PIE": False})
        self.assertEqual(strat1.strategy_name, "SHELLCODE_INJECTION")

        # Cenário 2: NX ativado sem Canary -> Ret2libc Stack Overflow
        strat2 = solver.evaluate_tactical_strategy({"NX": True, "Canary": False, "PIE": False})
        self.assertEqual(strat2.strategy_name, "RET2LIBC_STACK_OVERFLOW")

        # Cenário 3: NX, Canary e PIE ativados -> Leak Canary & ROP
        strat3 = solver.evaluate_tactical_strategy({"NX": True, "Canary": True, "PIE": True})
        self.assertEqual(strat3.strategy_name, "LEAK_CANARY_AND_ROP")


if __name__ == "__main__":
    unittest.main()
