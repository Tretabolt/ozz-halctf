"""
Bounded Context: Forensics Domain Solver
Responsabilidade Única (SRP): Análise forense de arquivos, esteganografia e metadados.
"""
from typing import List, Dict
from .base import BaseDomainSolver
from .registry import register_solver
from ..dtos.domain_dtos import AnalysisRequest, DomainAnalysisReport, CommandSpec

@register_solver("forensics")
@register_solver("stego")
class ForensicsDomainSolver(BaseDomainSolver):
    """Solver especializado em Forense Digital e Esteganografia."""

    @property
    def domain_type(self) -> str:
        return "forensics"

    def get_checklist(self, file_path: str = "evidence.file") -> List[Dict[str, str]]:
        return [
            {"name": "Metadata", "command": f"exiftool {file_path} 2>/dev/null"},
            {"name": "Embedded files", "command": f"binwalk {file_path} 2>/dev/null"},
            {"name": "Extract embedded", "command": f"binwalk -e {file_path} 2>/dev/null"},
            {"name": "Png stego", "command": f"zsteg {file_path} 2>/dev/null"},
        ]

    def analyze(self, request: AnalysisRequest) -> DomainAnalysisReport:
        spec = CommandSpec(binary="exiftool", args=[request.target_resource])
        exec_res = self.executor.execute(spec)
        return DomainAnalysisReport(
            domain=self.domain_type,
            success=exec_res.success,
            observations=[exec_res.output],
            metadata={"target": request.target_resource}
        )
