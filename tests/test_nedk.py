"""
TDD Tests for NEDK — Neural Executive Dynamic Kernel (Akita Way - Portão 5)
Tests the 4 MNHI 3.5 Mathematical Spaces: S(t), E(t), X(t), P(t)
"""
import os
import sys
import unittest
import hashlib
import json
import time

# Ensure agent package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestStateSpace(unittest.TestCase):
    """Tests for S(t) = (G, Φ, τ, J, I)"""

    def test_initial_state_empty(self):
        """S(0) deve ser um estado vazio válido"""
        from agent.nedk import StateSpace
        state = StateSpace()
        self.assertEqual(state.graph, {})
        self.assertEqual(state.workspace, {})
        self.assertEqual(state.invariants["flags_found"], 0)

    def test_add_target_updates_graph(self):
        """G(t) deve atualizar ao registrar um host descoberto"""
        from agent.nedk import StateSpace
        state = StateSpace()
        state.register_host("10.0.0.10", ports=[22, 80], services={"80": "nginx"})
        self.assertIn("10.0.0.10", state.graph)
        self.assertEqual(state.graph["10.0.0.10"]["ports"], [22, 80])

    def test_canonical_identity(self):
        """τ(t) deve gerar hash SHA-256 determinístico para um host"""
        from agent.nedk import StateSpace
        state = StateSpace()
        state.register_host("10.0.0.10", ports=[80, 22], services={"80": "nginx"})
        tau1 = state.canonical_hash("10.0.0.10")
        # Same data, different insertion order → same τ
        state2 = StateSpace()
        state2.register_host("10.0.0.10", ports=[22, 80], services={"80": "nginx"})
        tau2 = state2.canonical_hash("10.0.0.10")
        self.assertEqual(tau1, tau2)
        self.assertEqual(len(tau1), 64)  # SHA-256 hex digest

    def test_invariant_flags_count(self):
        """I(t) deve rastrear contagem de flags corretamente"""
        from agent.nedk import StateSpace
        state = StateSpace()
        state.record_flag("flag{test_1}")
        state.record_flag("flag{test_2}")
        self.assertEqual(state.invariants["flags_found"], 2)
        # Duplicate flag should not increment
        state.record_flag("flag{test_1}")
        self.assertEqual(state.invariants["flags_found"], 2)

    def test_snapshot_and_rollback(self):
        """σ(t) deve permitir snapshot e restore do estado"""
        from agent.nedk import StateSpace
        state = StateSpace()
        state.register_host("10.0.0.10", ports=[80])
        snapshot = state.snapshot()
        # Modify state
        state.register_host("10.0.0.20", ports=[22])
        self.assertIn("10.0.0.20", state.graph)
        # Rollback
        state.restore(snapshot)
        self.assertNotIn("10.0.0.20", state.graph)
        self.assertIn("10.0.0.10", state.graph)


class TestEventMesh(unittest.TestCase):
    """Tests for E(t) — Event pub/sub bus for δS perturbations"""

    def test_publish_subscribe(self):
        """δS publicado deve ser recebido por assinantes registrados"""
        from agent.nedk import EventMesh
        mesh = EventMesh()
        received = []
        mesh.subscribe("CLASS_I", lambda evt: received.append(evt))
        mesh.publish("CLASS_I", {"type": "scan_result", "data": "ports 22,80"})
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["type"], "scan_result")

    def test_event_classification(self):
        """Eventos devem ser classificados em Classe I (direto), II (derivado), III (externo)"""
        from agent.nedk import EventMesh
        mesh = EventMesh()
        class_i = []
        class_ii = []
        mesh.subscribe("CLASS_I", lambda evt: class_i.append(evt))
        mesh.subscribe("CLASS_II", lambda evt: class_ii.append(evt))
        mesh.publish("CLASS_I", {"source": "nmap"})
        mesh.publish("CLASS_II", {"source": "inference"})
        self.assertEqual(len(class_i), 1)
        self.assertEqual(len(class_ii), 1)

    def test_no_cross_delivery(self):
        """Eventos CLASS_I não devem ser entregues a assinantes CLASS_II"""
        from agent.nedk import EventMesh
        mesh = EventMesh()
        class_ii = []
        mesh.subscribe("CLASS_II", lambda evt: class_ii.append(evt))
        mesh.publish("CLASS_I", {"source": "nmap"})
        self.assertEqual(len(class_ii), 0)


class TestExecutive(unittest.TestCase):
    """Tests for X(t) = (Ω, A, P, R) — The offensive mind's decision core"""

    def test_scheduler_selects_target(self):
        """Ω deve selecionar o target com maior potencial de ganho"""
        from agent.nedk import Executive, StateSpace
        state = StateSpace()
        state.register_host("10.0.0.10", ports=[80], services={"80": "nginx"})
        state.register_host("10.0.0.20", ports=[22, 80, 443, 445], services={"80": "apache", "445": "samba"})
        executive = Executive()
        target = executive.schedule(state)
        # Target with more services should be prioritized
        self.assertEqual(target, "10.0.0.20")

    def test_prioritizer_scores_actions(self):
        """P deve calcular score de ganho tático para ações"""
        from agent.nedk import Executive
        executive = Executive()
        actions = [
            {"action": "nmap", "phase": "recon", "target": "10.0.0.10"},
            {"action": "sqlmap", "phase": "exploit", "target": "10.0.0.10"},
        ]
        ranked = executive.prioritize(actions)
        self.assertIsInstance(ranked, list)
        self.assertEqual(len(ranked), 2)
        # Each action should have a score
        self.assertIn("score", ranked[0])

    def test_risk_assessor(self):
        """R deve retornar avaliação de risco entre 0.0 e 1.0"""
        from agent.nedk import Executive
        executive = Executive()
        risk = executive.assess_risk({"action": "hydra", "target": "10.0.0.10"})
        self.assertGreaterEqual(risk, 0.0)
        self.assertLessEqual(risk, 1.0)

    def test_compute_control_signal(self):
        """u_Ω deve produzir um sinal de controle com target e phase"""
        from agent.nedk import Executive, StateSpace
        state = StateSpace()
        state.register_host("10.0.0.10", ports=[80])
        executive = Executive()
        control = executive.compute_control(state)
        self.assertIn("target", control)
        self.assertIn("phase", control)


class TestPsiStabilizer(unittest.TestCase):
    """Tests for Ψ-Stabilizer — Loop detector and anti-stagnation"""

    def test_detects_loop(self):
        """Deve detectar 3+ ações repetidas consecutivas"""
        from agent.nedk import PsiStabilizer
        stabilizer = PsiStabilizer()
        history = [
            {"action": "nmap", "target": "10.0.0.10"},
            {"action": "nmap", "target": "10.0.0.10"},
            {"action": "nmap", "target": "10.0.0.10"},
        ]
        self.assertTrue(stabilizer.detect_loop(history))

    def test_no_false_positive(self):
        """Não deve detectar loop com ações variadas"""
        from agent.nedk import PsiStabilizer
        stabilizer = PsiStabilizer()
        history = [
            {"action": "nmap", "target": "10.0.0.10"},
            {"action": "curl", "target": "10.0.0.10"},
            {"action": "gobuster", "target": "10.0.0.10"},
        ]
        self.assertFalse(stabilizer.detect_loop(history))

    def test_generates_perturbation(self):
        """Deve gerar uma perturbação δS com nova estratégia"""
        from agent.nedk import PsiStabilizer, StateSpace
        stabilizer = PsiStabilizer()
        state = StateSpace()
        state.register_host("10.0.0.10", ports=[80])
        state.register_host("10.0.0.20", ports=[22])
        perturbation = stabilizer.generate_perturbation(state)
        self.assertIn("action", perturbation)
        self.assertIn("reason", perturbation)


class TestNEDK(unittest.TestCase):
    """Tests for the NEDK orchestrator itself"""

    def test_nedk_instantiates(self):
        """NEDK deve instanciar com targets e conter todos os 4 espaços"""
        from agent.nedk import NEDK
        kernel = NEDK(targets=["10.0.0.10"], model_path="/models", dry_run=True)
        self.assertIsNotNone(kernel.state)
        self.assertIsNotNone(kernel.events)
        self.assertIsNotNone(kernel.executive)
        self.assertIsNotNone(kernel.stabilizer)

    def test_nedk_produces_report(self):
        """NEDK deve gerar relatório com estrutura válida"""
        from agent.nedk import NEDK
        kernel = NEDK(targets=["10.0.0.10"], model_path="/models", dry_run=True)
        report = kernel.generate_report()
        self.assertIn("status", report)
        self.assertIn("targets", report)
        self.assertIn("flags_found", report)
        self.assertIn("iterations", report)


if __name__ == "__main__":
    unittest.main()
