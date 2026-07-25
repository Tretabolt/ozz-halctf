"""
Bounded Context: Crypto Domain Solver
Responsabilidade Única (SRP): De-hashing, rotinas de decodificação e análise de cifras.
"""
import base64
import urllib.parse
from typing import Dict
from .base import BaseDomainSolver
from .registry import register_solver
from ..dtos.domain_dtos import AnalysisRequest, DomainAnalysisReport

@register_solver("crypto")
class CryptoDomainSolver(BaseDomainSolver):
    """Solver especializado para desafios de Criptografia."""

    @property
    def domain_type(self) -> str:
        return "crypto"

    def decode_string(self, payload: str) -> Dict[str, str]:
        results = {}
        try:
            results["base64"] = base64.b64decode(payload).decode("utf-8", errors="ignore")
        except Exception:
            pass
        return results

    def analyze(self, request: AnalysisRequest) -> DomainAnalysisReport:
        decoded = self.decode_string(request.target_resource)
        return DomainAnalysisReport(
            domain=self.domain_type,
            success=True,
            observations=[decoded],
            metadata={"target": request.target_resource}
        )
