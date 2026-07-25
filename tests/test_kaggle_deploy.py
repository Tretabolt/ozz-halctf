"""
TDD Tests for Kaggle Deployment Automation (Akita Way - Portão 5)
"""
import os
import json
import unittest

class TestKaggleDeploy(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.scripts_dir = os.path.join(self.base_dir, "scripts")
        self.metadata_path = os.path.join(self.scripts_dir, "kernel-metadata.json")
        self.notebook_path = os.path.join(self.scripts_dir, "ozz_kaggle.ipynb")

    def test_notebook_exists(self):
        """Verifica se o notebook ozz_kaggle.ipynb existe e é um JSON válido"""
        self.assertTrue(os.path.exists(self.notebook_path), "ozz_kaggle.ipynb não encontrado em scripts/")
        with open(self.notebook_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("cells", data, "Notebook inválido (sem cells)")

    def test_kernel_metadata_exists_and_valid(self):
        """Verifica se o kernel-metadata.json existe e possui a configuração correta para GPU"""
        self.assertTrue(os.path.exists(self.metadata_path), "kernel-metadata.json não encontrado em scripts/")
        with open(self.metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        self.assertIn("id", metadata, "Metadata deve conter 'id'")
        self.assertEqual(metadata.get("code_file"), "ozz_kaggle.ipynb", "code_file deve ser ozz_kaggle.ipynb")
        self.assertEqual(metadata.get("language"), "python", "language deve ser python")
        self.assertEqual(metadata.get("kernel_type"), "notebook", "kernel_type deve ser notebook")
        self.assertTrue(metadata.get("enable_gpu"), "enable_gpu deve ser True para o vLLM")
        self.assertTrue(metadata.get("enable_internet"), "enable_internet deve ser True para baixar modelo e pip")

if __name__ == "__main__":
    unittest.main()
