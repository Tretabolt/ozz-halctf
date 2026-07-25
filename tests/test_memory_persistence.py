"""
Suíte TDD de Persistência e Memória SQLite (Espaço P - BL-001)
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.memory import Memory
from agent.domains.hypothesis import Hypothesis, TournamentResult


class TestMemoryPersistence(unittest.TestCase):
    """Valida a persistência em banco SQLite temporário e a idempotência de registros (BL-001)."""

    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        self.memory = Memory(db_path=self.temp_db_path)

    def tearDown(self):
        os.close(self.temp_db_fd)
        if os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)

    def test_store_and_retrieve_findings(self):
        """1. Persistência e recuperação de achados e observações."""
        self.memory.store_finding(category="vuln", key="sqli", value="vulnerable", target="target.ctf")
        findings = self.memory.get_findings(target="target.ctf")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["key"], "sqli")

    def test_flag_storage_idempotency(self):
        """2. Idempotência de C: registrar a mesma flag duas vezes não duplica a entrada."""
        self.memory.store_flag("FLAG{test_123}", source="web", target="target.ctf")
        self.memory.store_flag("FLAG{test_123}", source="web", target="target.ctf")

        flags = self.memory.get_flags()
        self.assertEqual(len(flags), 1, "Mesma flag não deve ser duplicada no banco")

    def test_store_and_retrieve_tournament_results(self):
        """3. Registro e recuperação de histórico de Torneios de Hipóteses."""
        mock_winner = Hypothesis(id="h1", name="Análise EXIF", payload="exiftool")
        mock_result = TournamentResult(
            winner=mock_winner,
            ranked_hypotheses=[mock_winner],
            rounds_executed=1,
            debate_summary="Vencedora: Análise EXIF",
            history=[],
        )

        self.memory.store_tournament_result(domain="forensics", target="file.jpg", result=mock_result)
        history = self.memory.get_tournament_history(domain="forensics")

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["winner_name"], "Análise EXIF")
        self.assertEqual(history[0]["target"], "file.jpg")
        self.assertIn("Análise EXIF", history[0]["debate_summary"])

    def test_memory_stats(self):
        """4. Estatísticas de memória incluindo a tabela tournaments."""
        stats = self.memory.get_stats()
        self.assertIn("tournaments", stats)
        self.assertEqual(stats["tournaments"], 0)


if __name__ == "__main__":
    unittest.main()
