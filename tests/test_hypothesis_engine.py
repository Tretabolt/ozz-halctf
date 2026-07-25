"""
Suíte de Testes do Motor Tático de Torneio de Hipóteses (TacticalHypothesisEngine)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.domains.hypothesis import Hypothesis
from agent.domains.evaluator import FeatureScoringEvaluator, FeatureScorer
from agent.domains.mutator import StrategyMutatorPort
from agent.domains.engine import TacticalHypothesisEngine
from agent.security.security_barrier_policy import CommandAllowlistPolicy
from agent.dtos.domain_dtos import CommandSpec


class MockContextScorer(FeatureScorer):
    """Scorer para testes que atribui pontuação baseada no id da hipótese."""

    def evaluate(self, hypothesis: Hypothesis, context: dict) -> float:
        if hypothesis.id == "h_high":
            return 0.8
        elif hypothesis.id == "h_mid":
            return 0.5
        elif hypothesis.id == "h_low":
            return 0.2
        return hypothesis.initial_score


class MockMutator(StrategyMutatorPort):
    """Mutator para testes que gera uma hipótese variante."""

    def mutate(self, hypotheses: list, context: dict) -> list:
        return [
            Hypothesis(
                id=f"{h.id}_mutated",
                name=f"{h.name} Mutated",
                payload=CommandSpec(binary="exiftool", args=["mutated.jpg"]),
                initial_score=0.9,
            )
            for h in hypotheses
        ]


class TestHypothesisEngine(unittest.TestCase):
    """Valida o funcionamento do avaliador simétrico e do torneio Elo."""

    def test_pairwise_evaluator_symmetry(self):
        """A comparação Pairwise entre (h1, h2) e (h2, h1) deve produzir resultados perfeitamente simétricos."""
        evaluator = FeatureScoringEvaluator(scorer=MockContextScorer())
        h1 = Hypothesis(id="h_high", name="High", payload="p1", initial_score=0.8)
        h2 = Hypothesis(id="h_low", name="Low", payload="p2", initial_score=0.2)

        s1, s2 = evaluator.compare(h1, h2, context={})
        s2_rev, s1_rev = evaluator.compare(h2, h1, context={})

        self.assertAlmostEqual(s1, s1_rev, places=5)
        self.assertAlmostEqual(s2, s2_rev, places=5)
        self.assertAlmostEqual(s1 + s2, 1.0, places=5)

    def test_single_pass_tournament_execution(self):
        """Sem mutator, o torneio executa exatamente 1 rodada e ranqueia as hipóteses do maior para o menor Elo."""
        engine = TacticalHypothesisEngine(evaluator=FeatureScoringEvaluator(scorer=MockContextScorer()))
        hypotheses = [
            Hypothesis(id="h_low", name="Low", payload="p_low"),
            Hypothesis(id="h_high", name="High", payload="p_high"),
            Hypothesis(id="h_mid", name="Mid", payload="p_mid"),
        ]

        result = engine.run_tournament(hypotheses, context={}, max_rounds=1)
        self.assertEqual(result.rounds_executed, 1)
        self.assertEqual(result.winner.id, "h_high")
        self.assertEqual(result.ranked_hypotheses[0].id, "h_high")
        self.assertEqual(result.ranked_hypotheses[-1].id, "h_low")
        self.assertIn("Vencedora: 'High'", result.debate_summary)

    def test_total_rejection_raises_value_error(self):
        """Se a política de segurança descartar todas as hipóteses, o engine deve levantar ValueError."""
        policy = CommandAllowlistPolicy(frozenset({"exiftool"}))
        engine = TacticalHypothesisEngine()

        unsafe_hypotheses = [
            Hypothesis(id="h1", name="Unsafe", payload=CommandSpec(binary="nc", args=["10.0.0.1"])),
            Hypothesis(id="h2", name="Meta", payload=CommandSpec(binary="exiftool", args=["file.jpg; whoami"])),
        ]

        with self.assertRaises(ValueError) as ctx:
            engine.run_tournament(unsafe_hypotheses, context={}, policy=policy)
        self.assertIn("REJEIÇÃO_TOTAL", str(ctx.exception))

    def test_conditional_mutation_in_multi_round_tournament(self):
        """Ao injetar um mutator, o torneio executa múltiplos rounds e gera variantes evoluídas."""
        engine = TacticalHypothesisEngine(
            evaluator=FeatureScoringEvaluator(scorer=MockContextScorer()),
            mutator=MockMutator(),
        )
        policy = CommandAllowlistPolicy(frozenset({"exiftool"}))

        initial = [
            Hypothesis(id="h_high", name="High", payload=CommandSpec(binary="exiftool", args=["file.jpg"])),
            Hypothesis(id="h_low", name="Low", payload=CommandSpec(binary="exiftool", args=["file.png"])),
        ]

        result = engine.run_tournament(initial, context={}, policy=policy, max_rounds=2)
        self.assertEqual(result.rounds_executed, 2)
        self.assertTrue(any("mutated" in h.id for h in result.ranked_hypotheses))


if __name__ == "__main__":
    unittest.main()
