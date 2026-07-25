"""
Suíte de Testes de Contrato para o Adaptador de Ingestão/Recon (MNHI 3.5 - Espaço E)
Verifica as garantias do MANIFESTO-RECON-ADAPTER.md (CT-01 a CT-07)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestReconAdapterContract(unittest.TestCase):

    def test_ct01_tau_determinism(self):
        """CT-01: Determinismo de τ — dados idênticos com ordens/volatilidades diferentes devem gerar o mesmo τ"""
        from agent.recon_adapter.dtos import ReconRequest, TargetSpec, ToolProfile
        from agent.recon_adapter.orchestrator import ReconAdapterOrchestrator

        req = ReconRequest(
            request_id="req-1",
            target=TargetSpec(kind="DOMAIN", value="example.com"),
            tool_profile=ToolProfile(tool_name="nmap", tool_version_constraint="*", parser_version="1.0.0")
        )
        orchestrator = ReconAdapterOrchestrator()
        
        # Simula duas saídas brutas com variações de timestamp e ordem
        raw_out1 = "PORT 80/tcp open http\nPORT 22/tcp open ssh\n# Time: 12:00:00"
        raw_out2 = "# Time: 12:05:00\nPORT 22/tcp open ssh\nPORT 80/tcp open http"

        evt1 = orchestrator.process_raw(req, raw_out1)
        evt2 = orchestrator.process_raw(req, raw_out2)

        self.assertEqual(evt1.envelope.canonical_hash, evt2.envelope.canonical_hash, "τ deve ser determinístico")

    def test_ct03_domain_isolation_acl(self):
        """CT-03: Isolamento de domínio (ACL) — campos voláteis ou fora do schema devem ser descartados"""
        from agent.recon_adapter.mapper import DomainMapper
        mapper = DomainMapper()
        raw_data = {"host": "10.0.0.1", "port": 80, "unknown_field": "junk_data", "pid": 9999}
        mapped = mapper.map_to_domain(raw_data)
        
        self.assertNotIn("unknown_field", mapped.attributes)
        self.assertNotIn("pid", mapped.attributes)
        self.assertEqual(mapped.attributes.get("port"), 80)

    def test_ct06_modular_loc_limit(self):
        """CT-06: Granularidade modular — nenhum módulo em agent/recon_adapter/ pode exceder 70 LOC de lógica"""
        adapter_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agent", "recon_adapter")
        if not os.path.exists(adapter_dir):
            self.fail("Diretório agent/recon_adapter não existe")

        for filename in os.listdir(adapter_dir):
            if filename.endswith(".py"):
                filepath = os.path.join(adapter_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
                self.assertLessEqual(len(lines), 70, f"Módulo {filename} excedeu o limite de 70 LOC (total: {len(lines)})")

if __name__ == "__main__":
    unittest.main()
