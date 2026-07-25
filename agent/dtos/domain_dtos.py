"""Value Objects e DTOs Tipados para os Solvers de Domínio (<= 70 LOC)"""
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# Allowlist de caracteres seguros para shell=False.
# Mais robusto que denylist: metacaracteres não listados são inseguros por padrão.
# Cobre: letras, dígitos, hífen, underscore, ponto, barra, dois-pontos, espaço, igual.
# Rejeita: | ; > < $ ` " ' ( ) & \n e qualquer outro metacaractere de shell.
_SAFE_SHELL_RE = re.compile(r'^[a-zA-Z0-9_\-./: =]+\Z')  # \Z: sem exceção de newline final


@dataclass(frozen=True)
class ChecklistTemplate:
    """Template humano-legível de um passo de checklist.

    INVARIANTE DE SEGURANÇA: este tipo é deliberadamente incompatível com
    CommandSpec. O campo chama-se `human_readable_command` (não `args`).

    Para executar, use to_command_spec() — que levanta ValueError se o template
    contiver metacaracteres de shell (enforcement automático, não só deteção).
    """
    name: str
    human_readable_command: str
    description: str = ""

    def has_shell_metacharacters(self) -> bool:
        """Allowlist: True se o comando contém chars fora de [a-zA-Z0-9_\\-./: =].
        Mais robusto que denylist — metacaracteres desconhecidos são inseguros por padrão."""
        return not bool(_SAFE_SHELL_RE.match(self.human_readable_command))

    def to_command_spec(self, timeout: float = 60.0) -> "CommandSpec":
        """Único caminho canônico de conversão para CommandSpec.
        Levanta ValueError automaticamente se has_shell_metacharacters() for True.
        Não existe rota de copiar-colar que contorne este gate sem ser deliberada."""
        if self.has_shell_metacharacters():
            raise ValueError(
                f"ChecklistTemplate '{self.name}' não pode ser convertido para CommandSpec: "
                f"contém metacaracteres de shell (inclui '|', ';', '>', '$', etc.). "
                f"Comando: {self.human_readable_command!r}"
            )
        parts = self.human_readable_command.split()
        if not parts:
            raise ValueError(f"ChecklistTemplate '{self.name}' tem comando vazio.")
        return CommandSpec(binary=parts[0], args=parts[1:], timeout=timeout)


@dataclass(frozen=True)
class WebAttackTemplate:
    """Payload de ataque web (SQL Injection, LFI, XSS, etc.).

    NÃO é um comando de shell — opera na camada HTTP, não no SO.
    INVARIANTE: não tem to_command_spec() nem has_shell_metacharacters().
    Nunca passe a executor.execute(). O campo 'payload' é deliberadamente
    distinto de 'human_readable_command' e 'args' para evitar confusão.
    """
    name: str
    payload: str        # NÃO chamado 'command', 'human_readable_command' ou 'args'
    technique: str = ""


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
class TacticalStrategy:
    """Value Object representando uma estratégia de exploração tática decidida pelo domínio."""
    strategy_name: str
    target_vulnerability: str
    prerequisites: List[str] = field(default_factory=list)
    confidence: float = 1.0

@dataclass
class DomainAnalysisReport:
    """Relatório estruturado de análise retornado por um DomainSolver."""
    domain: str
    success: bool
    observations: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
