"""
TDD Tests for ReconAdapter ↔ NEDK Coupling (Akita Way - Portão 5)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestNedkReconCoupling(unittest.TestCase):

    def test_nedk_subscribes_to_recon_events(self):
        """Verifica se o NEDK inscreve o handler de recon no EventMesh"""
        from agent.nedk import NEDK
        kernel = NEDK(targets=["10.0.0.10"], dry_run=True)
        self.assertIn("CLASS_I", kernel.events.subscribers)
        self.assertGreater(len(kernel.events.subscribers["CLASS_I"]), 0)

    def test_recon_event_updates_state_space_graph(self):
        """Verifica se o envio de um EventClassI pelo ReconAdapter atualiza o G(t) no StateSpace"""
        from agent.nedk import NEDK
        from agent.recon_adapter.dtos import ReconRequest, TargetSpec, ToolProfile
        from agent.recon_adapter.orchestrator import ReconAdapterOrchestrator

        kernel = NEDK(targets=["10.0.0.10"], dry_run=True)
        recon_orchestrator = ReconAdapterOrchestrator(event_mesh_publish_func=kernel.events.publish)

        req = ReconRequest(
            request_id="req-test-1",
            target=TargetSpec(kind="IP", value="10.0.0.10"),
            tool_profile=ToolProfile(tool_name="nmap")
        )
        raw_output = "PORT 80/tcp open http\nPORT 22/tcp open ssh"
        
        # Processa e publica evento
        recon_orchestrator.process_raw(req, raw_output)

        # O StateSpace do NEDK deve ter atualizado o grafo G(t)
        host_data = kernel.state.graph.get("10.0.0.10")
        self.assertIsNotNone(host_data, "Host 10.0.0.10 deve existir no G(t)")
        self.assertIn(80, host_data["ports"], "Porta 80 deve ter sido registrada no G(t)")
        self.assertIn(22, host_data["ports"], "Porta 22 deve ter sido registrada no G(t)")

    def test_recon_event_triggers_canonical_hash_update(self):
        """Verifica se o evento do ReconAdapter atualiza a identidade canônica τ(t) do host"""
        from agent.nedk import NEDK
        from agent.recon_adapter.dtos import ReconRequest, TargetSpec, ToolProfile
        from agent.recon_adapter.orchestrator import ReconAdapterOrchestrator

        kernel = NEDK(targets=["10.0.0.10"], dry_run=True)
        tau_before = kernel.state.canonical_hash("10.0.0.10")

        recon_orchestrator = ReconAdapterOrchestrator(event_mesh_publish_func=kernel.events.publish)
        req = ReconRequest(
            request_id="req-test-2",
            target=TargetSpec(kind="IP", value="10.0.0.10"),
            tool_profile=ToolProfile(tool_name="nmap")
        )
        recon_orchestrator.process_raw(req, "PORT 8080/tcp open http-proxy")

        tau_after = kernel.state.canonical_hash("10.0.0.10")
        self.assertNotEqual(tau_before, tau_after, "τ(t) deve mudar após ingestão de novas portas")

if __name__ == "__main__":
    unittest.main()
