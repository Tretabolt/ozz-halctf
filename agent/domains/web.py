"""
Bounded Context: Web Domain Solver
Responsabilidade Única (SRP): Templates e ataques voltados a aplicações Web.
"""
from typing import Dict, Any
from .base import BaseDomainSolver
from .registry import register_solver
from ..dtos.domain_dtos import AnalysisRequest, DomainAnalysisReport

@register_solver("web")
class WebDomainSolver(BaseDomainSolver):
    """Solver especializado para segurança de aplicações Web."""

    @property
    def domain_type(self) -> str:
        return "web"

    def get_templates(self) -> Dict[str, Any]:
        return {
            "sqli_union": {
                "name": "SQL Injection — UNION",
                "detect": "' OR 1=1--",
            },
            "lfi": {
                "name": "Local File Inclusion",
                "basic": "../../../../etc/passwd",
            },
        }

    def analyze(self, request: AnalysisRequest) -> DomainAnalysisReport:
        return DomainAnalysisReport(
            domain=self.domain_type,
            success=True,
            observations=[self.get_templates()],
            metadata={"target": request.target_resource}
        )
