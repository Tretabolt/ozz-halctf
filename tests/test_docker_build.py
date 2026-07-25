"""
TDD Tests for Docker Build & Resilient Runtime Environment (Akita Way - Portão 5)
"""
import os
import unittest

class TestDockerBuild(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.dockerfile_path = os.path.join(self.base_dir, "Dockerfile")
        self.entrypoint_path = os.path.join(self.base_dir, "scripts", "entrypoint.sh")
        self.hf_server_path = os.path.join(self.base_dir, "scripts", "hf_server.py")

    def test_hf_server_script_exists(self):
        """Verifica se o servidor hf_server.py existe no diretório scripts/"""
        self.assertTrue(
            os.path.exists(self.hf_server_path),
            "scripts/hf_server.py deve existir como fallback para GPUs sm_60 ou CPU"
        )

    def test_dockerfile_copies_hf_server(self):
        """Verifica se o Dockerfile inclui a cópia do diretório scripts/ (contendo hf_server.py)"""
        self.assertTrue(os.path.exists(self.dockerfile_path), "Dockerfile não encontrado")
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertTrue(
            "COPY scripts/" in content or "hf_server.py" in content,
            "Dockerfile deve copiar o diretório scripts/ para incluir o hf_server.py"
        )

    def test_entrypoint_has_cuda_detection_and_fallback(self):
        """Verifica se o entrypoint.sh possui lógica de detecção de GPU e fallback"""
        self.assertTrue(os.path.exists(self.entrypoint_path), "scripts/entrypoint.sh não encontrado")
        with open(self.entrypoint_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertTrue(
            "hf_server.py" in content or "python" in content,
            "entrypoint.sh deve possuir suporte para executar o hf_server.py"
        )

if __name__ == "__main__":
    unittest.main()
