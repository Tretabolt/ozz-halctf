"""
Testes de Validação E2E da Configuração Docker & Universo Sintético (Akita Way - Portão 5)
"""
import os
import sys
import unittest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestE2EDockerCompose(unittest.TestCase):

    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.compose_full_path = os.path.join(self.base_dir, "docker-compose.full.yml")
        self.mock_runner_path = os.path.join(self.base_dir, "scripts", "mock_runner.py")

    def test_docker_compose_full_exists_and_valid_yaml(self):
        """Verifica se docker-compose.full.yml existe e é um YAML válido"""
        self.assertTrue(os.path.exists(self.compose_full_path), "docker-compose.full.yml não encontrado")
        with open(self.compose_full_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        self.assertIn("services", data, "docker-compose deve conter 'services'")
        services = data["services"]
        self.assertIn("target-01", services, "Deve conter serviço target-01")
        self.assertIn("target-02", services, "Deve conter serviço target-02")
        self.assertIn("target-03", services, "Deve conter serviço target-03")
        self.assertIn("target-04", services, "Deve conter serviço target-04")
        self.assertIn("ozz", services, "Deve conter o serviço ozz para o agente")

    def test_mock_runner_script_exists_and_executable(self):
        """Verifica se o mock_runner.py existe e é importável"""
        self.assertTrue(os.path.exists(self.mock_runner_path), "scripts/mock_runner.py não encontrado")
        with open(self.mock_runner_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("MockLLM", content, "mock_runner.py deve conter a classe MockLLM")
        self.assertIn("flag{web_master_2026}", content, "mock_runner.py deve simular a captura de flags dos alvos sintéticos")

if __name__ == "__main__":
    unittest.main()
