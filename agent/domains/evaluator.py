"""
Avaliador Simétrico e Feature Scorer para Torneios de Hipóteses (<= 70 LOC)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
from .hypothesis import Hypothesis


class FeatureScorer(ABC):
    """Contrato abstrato para pontuação isolada de hipóteses baseada em metadados."""

    @abstractmethod
    def evaluate(self, hypothesis: Hypothesis, context: Dict[str, Any]) -> float:
        """Calcula score de heurística contextual S(h_i) em [0.0, 1.0]."""
        pass


class DefaultFeatureScorer(FeatureScorer):
    """Scorer default que utiliza o initial_score da hipótese."""

    def evaluate(self, hypothesis: Hypothesis, context: Dict[str, Any]) -> float:
        return max(0.0, min(1.0, float(hypothesis.initial_score)))


class FeatureScoringEvaluator:
    """Avaliador de confronto direto Pairwise Simétrico entre duas hipóteses."""

    def __init__(self, scorer: FeatureScorer = None):
        self.scorer = scorer or DefaultFeatureScorer()

    def compare(
        self, h1: Hypothesis, h2: Hypothesis, context: Dict[str, Any]
    ) -> Tuple[float, float]:
        """Calcula a pontuação simétrica normalizada (s1, s2) para o confronto h1 vs h2.

        Formula:
            s1 = S(h1) / (S(h1) + S(h2))
            s2 = 1.0 - s1
            Se S(h1) + S(h2) == 0.0 -> (0.5, 0.5)
        """
        s1_raw = max(0.0, float(self.scorer.evaluate(h1, context)))
        s2_raw = max(0.0, float(self.scorer.evaluate(h2, context)))

        total = s1_raw + s2_raw
        if total == 0.0:
            return 0.5, 0.5

        s1 = s1_raw / total
        s2 = 1.0 - s1
        return s1, s2
