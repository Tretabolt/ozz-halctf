"""
DTOs para o Motor de Torneio de Hipóteses (<= 70 LOC)
"""
from dataclasses import dataclass, field
from typing import TypeVar, Generic, List, Dict, Any, Optional

T = TypeVar("T")


@dataclass
class Hypothesis(Generic[T]):
    """Representa uma hipótese tática submetida ao torneio de avaliação Elo."""
    id: str
    name: str
    payload: T
    initial_score: float = 0.5
    rating: float = 1200.0
    wins: int = 0
    losses: int = 0
    draws: int = 0

    @property
    def total_matches(self) -> int:
        return self.wins + self.losses + self.draws


@dataclass
class TournamentResult(Generic[T]):
    """Resultado estruturado de um torneio de hipóteses."""
    winner: Hypothesis[T]
    ranked_hypotheses: List[Hypothesis[T]]
    rounds_executed: int
    debate_summary: str
    history: List[Dict[str, Any]] = field(default_factory=list)
