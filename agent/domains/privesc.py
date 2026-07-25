"""
Bounded Context: Privesc Domain Solver
Responsabilidade Única (SRP): Auditoria de privilégios e elevação de acesso no SO.
"""
from typing import List, Dict, Any, FrozenSet
from .base import BaseDomainSolver
from .registry import register_solver
from .hypothesis import Hypothesis, TournamentResult
from .engine import TacticalHypothesisEngine
from ..security.security_barrier_policy import CommandAllowlistPolicy
from ..dtos.domain_dtos import AnalysisRequest, DomainAnalysisReport, CommandSpec, ChecklistTemplate

ALLOWED_PRIVESC_BINARIES: FrozenSet[str] = frozenset({"sudo", "find", "id", "uname"})


@register_solver("privesc")
class PrivescDomainSolver(BaseDomainSolver):
    """Solver especializado em Elevação de Privilégios com Engine de Torneio de Hipóteses."""

    def __init__(self, executor=None, file_reader=None, engine: TacticalHypothesisEngine = None):
        super().__init__(executor=executor, file_reader=file_reader)
        self.engine = engine or TacticalHypothesisEngine()
        self.security_policy = CommandAllowlistPolicy(ALLOWED_PRIVESC_BINARIES)

    @property
    def domain_type(self) -> str:
        return "privesc"

    def get_checklist(self, scope: str = "local") -> List[ChecklistTemplate]:
        return [
            ChecklistTemplate(
                name="Sudo privileges",
                human_readable_command="sudo -l",
                description="Lista regras de sudo permitidas para o usuário atual."
            ),
            ChecklistTemplate(
                name="SUID Binaries",
                human_readable_command="find / -perm -4000",
                description="Audita binários com bit SUID ativado."
            ),
            ChecklistTemplate(
                name="Current user identity",
                human_readable_command="id",
                description="Exibe UID, GID e grupos do usuário ativo."
            ),
        ]

    def solve_tactical_step(self, metadata: Dict[str, Any]) -> TournamentResult[CommandSpec]:
        """Gera, sanitiza e ranqueia hipóteses táticas de auditoria de privilégios via Torneio Elo."""
        user_level = str(metadata.get("user_level", "low_privilege")).lower()

        hyp_sudo_score = 0.95 if user_level == "low_privilege" else 0.6
        hyp_suid_score = 0.85 if user_level == "low_privilege" else 0.5
        hyp_id_score = 0.99 if user_level == "unknown" else 0.4
        hyp_uname_score = 0.7 if user_level == "low_privilege" else 0.3

        hypotheses = [
            Hypothesis(
                id="hyp_sudo_l",
                name="Auditoria de Regras Sudo Sem Senha",
                payload=CommandSpec(binary="sudo", args=["-l"]),
                initial_score=hyp_sudo_score,
            ),
            Hypothesis(
                id="hyp_suid_find",
                name="Busca de Binários com Bit SUID",
                payload=CommandSpec(binary="find", args=["/", "-perm", "-4000"]),
                initial_score=hyp_suid_score,
            ),
            Hypothesis(
                id="hyp_user_id",
                name="Verificação da Identidade e Grupos",
                payload=CommandSpec(binary="id", args=[]),
                initial_score=hyp_id_score,
            ),
            Hypothesis(
                id="hyp_kernel_uname",
                name="Inspeção da Versão do Kernel OS",
                payload=CommandSpec(binary="uname", args=["-a"]),
                initial_score=hyp_uname_score,
            ),
        ]

        return self.engine.run_tournament(
            hypotheses, context=metadata, policy=self.security_policy
        )

    def analyze(self, request: AnalysisRequest) -> DomainAnalysisReport:
        user_level = request.options.get("user_level", "low_privilege")
        tournament_res = self.solve_tactical_step({"user_level": user_level})
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
