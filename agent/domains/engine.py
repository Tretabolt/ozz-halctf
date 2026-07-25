"""
Motor Tático de Torneio de Hipóteses com Elo Pairwise (<= 70 LOC)
"""
import math
from typing import List, Dict, Any, Optional, TypeVar
from .hypothesis import Hypothesis, TournamentResult
from .evaluator import FeatureScoringEvaluator
from .mutator import StrategyMutatorPort
from ..security.security_barrier_policy import CommandAllowlistPolicy
from ..dtos.domain_dtos import CommandSpec

T = TypeVar("T")


class TacticalHypothesisEngine:
    """Orquestrador do Torneio de Hipóteses (Test-Time Compute Engine)."""

    def __init__(
        self,
        evaluator: Optional[FeatureScoringEvaluator] = None,
        mutator: Optional[StrategyMutatorPort] = None,
        k_factor: float = 32.0,
    ):
        self.evaluator = evaluator or FeatureScoringEvaluator()
        self.mutator = mutator
        self.k_factor = k_factor

    def _sanitize_hypotheses(
        self, hypotheses: List[Hypothesis[T]], policy: Optional[CommandAllowlistPolicy]
    ) -> List[Hypothesis[T]]:
        if not policy:
            return hypotheses
        valid: List[Hypothesis[T]] = []
        for h in hypotheses:
            if isinstance(h.payload, CommandSpec):
                ok, _ = policy.validate_command(h.payload.binary, h.payload.args)
                if ok:
                    valid.append(h)
            elif isinstance(h.payload, dict) and "binary" in h.payload and "args" in h.payload:
                ok, _ = policy.validate_command(h.payload["binary"], h.payload["args"])
                if ok:
                    valid.append(h)
            else:
                valid.append(h)
        return valid

    def run_tournament(
        self,
        hypotheses: List[Hypothesis[T]],
        context: Dict[str, Any],
        policy: Optional[CommandAllowlistPolicy] = None,
        max_rounds: int = 1,
    ) -> TournamentResult[T]:
        sanitized = self._sanitize_hypotheses(hypotheses, policy)
        if not sanitized:
            raise ValueError("REJEIÇÃO_TOTAL: Todas as hipóteses foram descartadas pela política de segurança.")

        pool = list(sanitized)
        rounds_to_run = 1 if self.mutator is None else max(1, max_rounds)
        history: List[Dict[str, Any]] = []

        for round_idx in range(1, rounds_to_run + 1):
            n = len(pool)
            for i in range(n):
                for j in range(i + 1, n):
                    h1, h2 = pool[i], pool[j]
                    e1 = 1.0 / (1.0 + math.pow(10.0, (h2.rating - h1.rating) / 400.0))
                    e2 = 1.0 - e1

                    s1, s2 = self.evaluator.compare(h1, h2, context)

                    h1.rating += self.k_factor * (s1 - e1)
                    h2.rating += self.k_factor * (s2 - e2)

                    if s1 > s2:
                        h1.wins += 1; h2.losses += 1
                    elif s2 > s1:
                        h2.wins += 1; h1.losses += 1
                    else:
                        h1.draws += 1; h2.draws += 1

                    history.append({"round": round_idx, "h1": h1.id, "h2": h2.id, "s1": s1, "s2": s2})

            if self.mutator and round_idx < rounds_to_run and len(pool) > 1:
                pool.sort(key=lambda h: h.rating, reverse=True)
                cutoff = max(1, len(pool) // 2)
                survivors = pool[:cutoff]
                mutated = self.mutator.mutate(survivors, context)
                sanitized_mutated = self._sanitize_hypotheses(mutated, policy)
                pool = survivors + sanitized_mutated

        pool.sort(key=lambda h: h.rating, reverse=True)
        winner = pool[0]
        summary = (
            f"Torneio finalizado com {len(pool)} hipóteses em {rounds_to_run} rodada(s). "
            f"Vencedora: '{winner.name}' (id={winner.id}, rating={winner.rating:.1f})."
        )
        return TournamentResult(
            winner=winner,
            ranked_hypotheses=pool,
            rounds_executed=rounds_to_run,
            debate_summary=summary,
            history=history,
        )
