"""
Bounded Context: Web Domain Solver
Responsabilidade Única (SRP): Enumeração HTTP, inspeção de rotas e segurança Web.
"""
from typing import Dict, Any, FrozenSet
from .base import BaseDomainSolver
from .registry import register_solver
from .hypothesis import Hypothesis, TournamentResult
from .engine import TacticalHypothesisEngine
from ..security.security_barrier_policy import CommandAllowlistPolicy
from ..dtos.domain_dtos import AnalysisRequest, DomainAnalysisReport, CommandSpec, WebAttackTemplate

ALLOWED_WEB_BINARIES: FrozenSet[str] = frozenset({"curl", "nmap"})


@register_solver("web")
class WebDomainSolver(BaseDomainSolver):
    """Solver especializado em segurança de aplicações Web com Engine de Torneio de Hipóteses."""

    def __init__(self, executor=None, file_reader=None, engine: TacticalHypothesisEngine = None):
        super().__init__(executor=executor, file_reader=file_reader)
        self.engine = engine or TacticalHypothesisEngine()
        self.security_policy = CommandAllowlistPolicy(ALLOWED_WEB_BINARIES)

    @property
    def domain_type(self) -> str:
        return "web"

    def get_templates(self) -> Dict[str, WebAttackTemplate]:
        return {
            "sqli_union": WebAttackTemplate(
                name="SQL Injection — UNION",
                payload="' OR 1=1--",
                technique="sqli",
            ),
            "lfi": WebAttackTemplate(
                name="Local File Inclusion",
                payload="../../../../etc/passwd",
                technique="lfi",
            ),
        }

    def solve_tactical_step(self, metadata: Dict[str, Any]) -> TournamentResult[CommandSpec]:
        """Gera, sanitiza e ranqueia hipóteses táticas de enumeração Web via Torneio Elo."""
        target = str(metadata.get("target_resource", "http://localhost"))
        target_type = str(metadata.get("target_type", "http")).lower()

        hyp_headers_score = 0.95 if target_type == "http" or "http" in target else 0.5
        hyp_robots_score = 0.85 if "http" in target else 0.4
        hyp_options_score = 0.7 if "http" in target else 0.3
        hyp_nmap_score = 0.9 if target_type == "port_scan" or "http" not in target else 0.3

        robots_url = f"{target.rstrip('/')}/robots.txt"

        hypotheses = [
            Hypothesis(
                id="hyp_headers",
                name="Inspeção de Cabeçalhos HTTP Response",
                payload=CommandSpec(binary="curl", args=["-I", target]),
                initial_score=hyp_headers_score,
            ),
            Hypothesis(
                id="hyp_robots",
                name="Consulta ao robots.txt",
                payload=CommandSpec(binary="curl", args=["-s", robots_url]),
                initial_score=hyp_robots_score,
            ),
            Hypothesis(
                id="hyp_options",
                name="Verificação de Métodos HTTP Permitidos",
                payload=CommandSpec(binary="curl", args=["-X", "OPTIONS", "-I", target]),
                initial_score=hyp_options_score,
            ),
            Hypothesis(
                id="hyp_nmap_web",
                name="Detecção de Serviços Web via Nmap",
                payload=CommandSpec(binary="nmap", args=["-sV", "-p", "80,443", target]),
                initial_score=hyp_nmap_score,
            ),
        ]

        return self.engine.run_tournament(
            hypotheses, context=metadata, policy=self.security_policy
        )

    def analyze(self, request: AnalysisRequest) -> DomainAnalysisReport:
        tournament_res = self.solve_tactical_step({
            "target_resource": request.target_resource,
            "target_type": request.options.get("target_type", "http"),
        })
        winning_cmd = tournament_res.winner.payload

        exec_res = self.executor.execute(winning_cmd)
        errors = [exec_res.error] if exec_res.error else []

        return DomainAnalysisReport(
            domain=self.domain_type,
            success=exec_res.success,
            observations=[exec_res.output] if exec_res.success else [],
            errors=errors,
            metadata={
                "target": request.target_resource,
                "winning_hypothesis": tournament_res.winner.name,
                "debate_summary": tournament_res.debate_summary,
            }
        )
