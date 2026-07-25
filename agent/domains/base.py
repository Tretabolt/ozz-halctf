"""Interface Base para Solvers de Domínio (<= 70 LOC)"""
from abc import ABC, abstractmethod
from typing import Optional
from ..ports.executor import ProcessExecutorPort
from ..infra.executor import SafeProcessExecutor
from ..dtos.domain_dtos import AnalysisRequest, DomainAnalysisReport

class BaseDomainSolver(ABC):
    """Contrato base para Solvers de Domínio Hexagonais."""

    def __init__(self, executor: Optional[ProcessExecutorPort] = None):
        self.executor = executor or SafeProcessExecutor()

    @property
    @abstractmethod
    def domain_type(self) -> str:
        """Tipo de domínio delimitado (ex: pwn, web, forensics)."""
        pass

    @abstractmethod
    def analyze(self, request: AnalysisRequest) -> DomainAnalysisReport:
        """Executa a análise tipada do domínio."""
        pass
