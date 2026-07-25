"""Porta de Infraestrutura: ProcessExecutorPort (<= 70 LOC)"""
from abc import ABC, abstractmethod
from typing import List
from ..dtos.domain_dtos import CommandSpec, ExecutionResult

class ProcessExecutorPort(ABC):
    """Interface abstrata para execução segura de comandos no SO."""

    @abstractmethod
    def execute(self, spec: CommandSpec) -> ExecutionResult:
        """Executa especificação de comando isolada."""
        pass


class MockProcessExecutor(ProcessExecutorPort):
    """Mock Executor para testes unitários de domínio sem invocar o SO."""

    def __init__(self, mock_output: str = "mock stdout", exit_code: int = 0):
        self.mock_output = mock_output
        self.exit_code = exit_code
        self.executed_commands: List[CommandSpec] = []

    def execute(self, spec: CommandSpec) -> ExecutionResult:
        self.executed_commands.append(spec)
        return ExecutionResult(
            output=self.mock_output,
            exit_code=self.exit_code,
            success=(self.exit_code == 0)
        )
