"""
Porta da Interface de Mutação de Hipóteses (<= 70 LOC)
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, TypeVar
from .hypothesis import Hypothesis

T = TypeVar("T")


class StrategyMutatorPort(ABC):
    """Porta para mutação e evolução de hipóteses em Test-Time Compute."""

    @abstractmethod
    def mutate(
        self, hypotheses: List[Hypothesis[T]], context: Dict[str, Any]
    ) -> List[Hypothesis[T]]:
        """Gera novas variantes mutadas a partir das hipóteses de menor desempenho."""
        pass
