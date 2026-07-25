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
        rev_checklist = arsenal.reverse_engineering_checklist("untrusted_bin")
        for item in rev_checklist:
            cmd = item.human_readable_command  # ChecklistTemplate — não dict
            self.assertNotIn("ldd ", cmd, "USO PERIGOSO DE 'ldd' DETECTADO! Deve usar 'readelf -d' estático.")
            self.assertNotIn("ldd\t", cmd)
            self.assertFalse(cmd.startswith("ldd"), "USO PERIGOSO DE 'ldd' DETECTADO!")

    def test_readelf_static_analysis_used(self):
        """Verifica se a análise estática segura via readelf substituiu o ldd"""
        from agent.exploits import ExploitArsenal
        arsenal = ExploitArsenal()
        rev_checklist = arsenal.reverse_engineering_checklist("untrusted_bin")
        commands = [item.human_readable_command for item in rev_checklist]  # ChecklistTemplate — não dict
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


class TestChecklistTemplateSafetyBarrier(unittest.TestCase):
    """Valida a barreira estrutural de tipo entre ChecklistTemplate e CommandSpec."""

    def test_checklist_returns_checklist_template_not_dict(self):
        """get_checklist() deve retornar List[ChecklistTemplate], não dicionários crús."""
        from agent.domains.pwn_rev import PwnRevDomainSolver
        from agent.dtos.domain_dtos import ChecklistTemplate
        solver = PwnRevDomainSolver()
        checklist = solver.get_checklist()
        for item in checklist:
            self.assertIsInstance(
                item, ChecklistTemplate,
                f"Item deveria ser ChecklistTemplate, não {type(item).__name__}"
            )

    def test_allowlist_catches_pipe_metacharacter(self):
        """Allowlist deve detectar '|' mesmo sem espaço (bug do denylist 'pipe+espaço' corrigido)."""
        from agent.dtos.domain_dtos import ChecklistTemplate
        # Pipe colado sem espaço — o denylist anterior '"| "' não pegava isso
        colado = ChecklistTemplate(name="t", human_readable_command="strings /bin/x|grep flag")
        self.assertTrue(colado.has_shell_metacharacters())
        # Pipe com espaço — também deve ser detectado
        spaced = ChecklistTemplate(name="t", human_readable_command="strings /bin/x | grep flag")
        self.assertTrue(spaced.has_shell_metacharacters())

    def test_allowlist_catches_redirection_operator(self):
        """Allowlist detecta '>' (redireção shell) que o denylist anterior não cobria."""
        from agent.dtos.domain_dtos import ChecklistTemplate
        redir = ChecklistTemplate(
            name="readelf com redirect",
            human_readable_command="readelf -d /bin/ls 2>/dev/null"
        )
        self.assertTrue(redir.has_shell_metacharacters(),
            "'2>/dev/null' contém '>' — deve ser sinalizado como inseguro para shell=False")

    def test_safe_template_has_no_metacharacters(self):
        """Templates sem metacaracteres passam na allowlist."""
        from agent.dtos.domain_dtos import ChecklistTemplate
        safe = ChecklistTemplate(name="readelf", human_readable_command="readelf -d /bin/ls")
        self.assertFalse(safe.has_shell_metacharacters())

    def test_to_command_spec_raises_on_unsafe_template(self):
        """to_command_spec() levanta ValueError automaticamente para templates com metacaracteres."""
        from agent.dtos.domain_dtos import ChecklistTemplate
        unsafe = ChecklistTemplate(
            name="strings com pipe",
            human_readable_command="strings /bin/ls | grep flag"
        )
        with self.assertRaises(ValueError) as ctx:
            unsafe.to_command_spec()
        self.assertIn("metacaracteres de shell", str(ctx.exception))

    def test_to_command_spec_succeeds_on_safe_template(self):
        """to_command_spec() converte corretamente templates sem metacaracteres."""
        from agent.dtos.domain_dtos import ChecklistTemplate, CommandSpec
        safe = ChecklistTemplate(name="readelf", human_readable_command="readelf -d /bin/ls")
        spec = safe.to_command_spec()
        self.assertIsInstance(spec, CommandSpec)
        self.assertEqual(spec.binary, "readelf")
        self.assertEqual(spec.args, ["-d", "/bin/ls"])

    def test_checklist_template_is_not_command_spec(self):
        """ChecklistTemplate não deve ser instância de CommandSpec (barreira de tipo real)."""
        from agent.dtos.domain_dtos import ChecklistTemplate, CommandSpec
        template = ChecklistTemplate(name="t", human_readable_command="strings binary")
        self.assertNotIsInstance(template, CommandSpec)
        self.assertFalse(hasattr(template, "args"),
            "ChecklistTemplate não deve ter 'args' para evitar confusão com CommandSpec")

    def test_web_attack_template_has_no_to_command_spec(self):
        """WebAttackTemplate não deve ter to_command_spec() — payloads web não são comandos de SO."""
        from agent.dtos.domain_dtos import WebAttackTemplate
        payload = WebAttackTemplate(name="SQLi", payload="' OR 1=1--", technique="sqli")
        self.assertFalse(hasattr(payload, "to_command_spec"),
            "WebAttackTemplate não deve ter to_command_spec() — não é um comando de shell")
        self.assertFalse(hasattr(payload, "human_readable_command"),
            "WebAttackTemplate usa 'payload', não 'human_readable_command'")

    def test_web_domain_solver_returns_web_attack_template(self):
        """WebDomainSolver.get_templates() deve retornar WebAttackTemplate, não dict cru."""
        from agent.domains.web import WebDomainSolver
        from agent.dtos.domain_dtos import WebAttackTemplate
        solver = WebDomainSolver()
        templates = solver.get_templates()
        for key, item in templates.items():
            self.assertIsInstance(item, WebAttackTemplate,
                f"Template '{key}' deveria ser WebAttackTemplate, não {type(item).__name__}")
            self.assertTrue(hasattr(item, "payload"),
                "WebAttackTemplate deve ter campo 'payload'")
            self.assertFalse(hasattr(item, "human_readable_command"),
                "WebAttackTemplate não deve ter 'human_readable_command'")


if __name__ == "__main__":
    unittest.main()
