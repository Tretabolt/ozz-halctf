"""
Suíte TDD de Arquitetura, Segurança e Resiliência a Falhas (Portão 5 - RED)
Valida a separação DDD em Bounded Contexts, eliminação do ldd inseguro e tratamento de dados corrompidos.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDDDDomainArchitecture(unittest.TestCase):
    """Valida a separação em Bounded Contexts (DDD / SRP)"""

    def test_bounded_contexts_exist(self):
        """Verifica se os solvers de domínio existem no pacote agent.domains"""
        from agent.domains.web import WebDomainSolver
        from agent.domains.privesc import PrivescDomainSolver
        from agent.domains.forensics import ForensicsDomainSolver
        from agent.domains.pwn_rev import PwnRevDomainSolver
        from agent.domains.crypto import CryptoDomainSolver

        self.assertIsNotNone(WebDomainSolver)
        self.assertIsNotNone(PrivescDomainSolver)
        self.assertIsNotNone(ForensicsDomainSolver)
        self.assertIsNotNone(PwnRevDomainSolver)
        self.assertIsNotNone(CryptoDomainSolver)

    def test_exploit_arsenal_is_facade(self):
        """Verifica se ExploitArsenal atua como Façade delegadora"""
        from agent.exploits import ExploitArsenal
        arsenal = ExploitArsenal()
        self.assertTrue(hasattr(arsenal, "web_solver"), "Arsenal deve conter referência ao WebDomainSolver")
        self.assertTrue(hasattr(arsenal, "pwn_solver"), "Arsenal deve conter referência ao PwnRevDomainSolver")


class TestSecurityAndIsolation(unittest.TestCase):
    """Valida a eliminação do ldd e sanitização de segurança"""

    def test_no_ldd_usage_in_checklists(self):
        """Garante que NENHUM checklist executa 'ldd' em binários não confiáveis (RCE vulnerability)"""
        from agent.exploits import ExploitArsenal
        arsenal = ExploitArsenal()
        
        # Inspeciona comandos do checklist de reversão
        rev_checklist = arsenal.reverse_engineering_checklist("untrusted_bin")
        for item in rev_checklist:
            cmd = item.get("command", "")
            self.assertNotIn("ldd ", cmd, "USO PERIGOSO DE 'ldd' DETECTADO! Deve usar 'readelf -d' estático.")
            self.assertNotIn("ldd\t", cmd)
            self.assertFalse(cmd.startswith("ldd"), "USO PERIGOSO DE 'ldd' DETECTADO!")

    def test_readelf_static_analysis_used(self):
        """Verifica se a análise estática segura via readelf substituiu o ldd"""
        from agent.exploits import ExploitArsenal
        arsenal = ExploitArsenal()
        rev_checklist = arsenal.reverse_engineering_checklist("untrusted_bin")
        commands = [item.get("command", "") for item in rev_checklist]
        has_static_readelf = any("readelf" in cmd for cmd in commands)
        self.assertTrue(has_static_readelf, "Checklist de reversão deve usar readelf para inspeção estática segura")


class TestEdgeCaseAndCorruptDataResilience(unittest.TestCase):
    """Valida resiliência contra saídas corrompidas e estouro de limites"""

    def test_parser_corrupted_garbage_input(self):
        """RawResultParser deve processar dados corrompidos/binários sem lançar exceção não tratada"""
        from agent.recon_adapter.parser import RawResultParser
        parser = RawResultParser()
        garbage_raw = "\x00\xff\xfe\xfd\x00\x01INVALID_HEADER_GARBAGE!!!<<<>>>"
        parsed = parser.parse(garbage_raw, "nmap")
        self.assertIsInstance(parsed, list, "Parser deve retornar lista tratada mesmo para dados corrompidos")

    def test_validator_resource_limit_rejection(self):
        """RequestValidator deve rejeitar explicitamente requisições que excedem limites sem quebrar o sistema"""
        from agent.recon_adapter.dtos import ReconRequest, TargetSpec, ToolProfile
        from agent.recon_adapter.validator import RequestValidator

        validator = RequestValidator(max_timeout=600.0, max_memory_mb=1024)
        excessive_req = ReconRequest(
            request_id="req-limit-1",
            target=TargetSpec(kind="IP", value="10.0.0.10"),
            tool_profile=ToolProfile(tool_name="nmap"),
            hard_timeout=9999.0,  # Excede limite
            memory_limit_mb=4096   # Excede limite
        )
        with self.assertRaises(ValueError) as ctx:
            validator.validate(excessive_req)
        self.assertIn("RESOURCE_LIMIT_EXCEEDED", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
