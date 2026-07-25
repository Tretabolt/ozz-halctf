"""DomainSolverRegistry desacoplado cumprindo o OCP (<= 70 LOC)"""
from typing import Dict, Type, Optional
from .base import BaseDomainSolver

class DomainSolverRegistry:
    """Registro dinâmico de Solvers de Domínio (Open/Closed Principle)."""
    _solvers: Dict[str, Type[BaseDomainSolver]] = {}

    @classmethod
    def register(cls, domain_type: str, solver_cls: Type[BaseDomainSolver]):
        cls._solvers[domain_type] = solver_cls

    @classmethod
    def has_solver(cls, domain_type: str) -> bool:
        return domain_type in cls._solvers

    @classmethod
    def get_solver(cls, domain_type: str) -> Optional[BaseDomainSolver]:
        solver_cls = cls._solvers.get(domain_type)
        return solver_cls() if solver_cls else None

    @classmethod
    def list_domains(cls) -> list[str]:
        return list(cls._solvers.keys())


def register_solver(domain_type: str):
    """Decorador para registrar novos Solvers no Registry automaticamente."""
    def decorator(cls: Type[BaseDomainSolver]):
        DomainSolverRegistry.register(domain_type, cls)
        return cls
    return decorator
