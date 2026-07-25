"""
Suíte TDD de Treinamento CTF (Akita Way - Portão 5)
Testa capacidades expandidas de Criptografia, Reversão e Forense
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestCtfTraining(unittest.TestCase):

    def test_crypto_few_shot_presence(self):
        """Verifica se existem exemplos few-shot calibrando o agente para Criptografia"""
        from agent.few_shot import FEW_SHOT_EXAMPLES
        crypto_examples = [
            ex for ex in FEW_SHOT_EXAMPLES 
            if "crypto" in ex["content"].lower() or "base64" in ex["content"].lower() or "rsa" in ex["content"].lower()
        ]
        self.assertGreaterEqual(len(crypto_examples), 1, "Devem existir exemplos few-shot de Criptografia")

    def test_forensics_tools_presence(self):
        """Verifica se ferramentas de Forense/Stego estão registradas na ToolRegistry"""
        from agent.tools import ToolRegistry
        registry = ToolRegistry()
        tools = registry.tools
        self.assertIn("exiftool", tools, "Ferramenta exiftool deve estar registrada")
        self.assertIn("binwalk", tools, "Ferramenta binwalk deve estar registrada")

    def test_pwntools_and_rev_helpers(self):
        """Verifica se ajudantes de engenharia reversa e pwn estão disponíveis no arsenal"""
        from agent.exploits import ExploitArsenal
        arsenal = ExploitArsenal()
        self.assertTrue(hasattr(arsenal, "reverse_engineering_checklist"), "Arsenal deve conter checklist de reversão")

if __name__ == "__main__":
    unittest.main()
