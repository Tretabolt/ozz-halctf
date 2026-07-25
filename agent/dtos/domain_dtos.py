"""Value Objects e DTOs Tipados para os Solvers de Domínio (<= 70 LOC)"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class CommandSpec:
    """Especificação de comando parametrizado (shell=False)."""
    binary: str
    args: List[str] = field(default_factory=list)
    timeout: float = 60.0

@dataclass
class ExecutionResult:
    """Resultado da execução via ProcessExecutorPort."""
    output: str
    exit_code: int
    success: bool
    error: Optional[str] = None

@dataclass
class AnalysisRequest:
    """Requisição de análise agnóstica de domínio."""
    domain: str
    target_resource: str
    options: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DomainAnalysisReport:
    """Relatório estruturado de análise retornado por um DomainSolver."""
    domain: str
    success: bool
    observations: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
