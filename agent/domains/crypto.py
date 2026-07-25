"""
Bounded Context: Crypto Domain Solver
Responsabilidade Única (SRP): Decodificação, inspeção de cifras e análise de formatos criptográficos.
"""
from typing import Dict, Any, FrozenSet
from .base import BaseDomainSolver
from .registry import register_solver
from .hypothesis import Hypothesis, TournamentResult
from .engine import TacticalHypothesisEngine
from ..security.security_barrier_policy import CommandAllowlistPolicy
from ..dtos.domain_dtos import AnalysisRequest, DomainAnalysisReport, CommandSpec

ALLOWED_CRYPTO_BINARIES: FrozenSet[str] = frozenset({"base64", "xxd", "openssl"})


@register_solver("crypto")
class CryptoDomainSolver(BaseDomainSolver):
    """Solver especializado em Criptografia com Engine de Torneio de Hipóteses."""

    def __init__(self, executor=None, file_reader=None, engine: TacticalHypothesisEngine = None):
        super().__init__(executor=executor, file_reader=file_reader)
        self.engine = engine or TacticalHypothesisEngine()
        self.security_policy = CommandAllowlistPolicy(ALLOWED_CRYPTO_BINARIES)

    @property
    def domain_type(self) -> str:
        return "crypto"

    def solve_tactical_step(self, metadata: Dict[str, Any]) -> TournamentResult[CommandSpec]:
        """Gera, sanitiza e ranqueia hipóteses táticas de análise criptográfica via Torneio Elo."""
        target = str(metadata.get("target_resource", "cipher.txt"))
        data_format = str(metadata.get("data_format", "base64")).lower()

        hyp_base64_score = 0.95 if data_format == "base64" or "b64" in target else 0.4
        hyp_xxd_score = 0.9 if data_format == "hex" or data_format == "binary_dump" else 0.5
        hyp_pem_score = 0.95 if data_format == "pem" or "pem" in target or "key" in target else 0.3

        hypotheses = [
            Hypothesis(
                id="hyp_base64_decode",
                name="Decodificação Base64",
                payload=CommandSpec(binary="base64", args=["-d", target]),
                initial_score=hyp_base64_score,
            ),
            Hypothesis(
                id="hyp_xxd_hexdump",
                name="Inspeção de Dump Hexadecimal",
                payload=CommandSpec(binary="xxd", args=[target]),
                initial_score=hyp_xxd_score,
            ),
            Hypothesis(
                id="hyp_openssl_asn1",
                name="Análise de Estrutura ASN1/PEM via OpenSSL",
                payload=CommandSpec(binary="openssl", args=["asn1parse", "-in", target]),
                initial_score=hyp_pem_score,
            ),
        ]

        return self.engine.run_tournament(
            hypotheses, context=metadata, policy=self.security_policy
        )

    def analyze(self, request: AnalysisRequest) -> DomainAnalysisReport:
        data_format = request.options.get("data_format", "base64")
        tournament_res = self.solve_tactical_step({
            "target_resource": request.target_resource,
            "data_format": data_format,
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
