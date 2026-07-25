"""
Bounded Context: Forensics Domain Solver
Responsabilidade Única (SRP): Análise forense digital, esteganografia e metadados.
"""
from typing import List, Dict, Any, FrozenSet
from .base import BaseDomainSolver
from .registry import register_solver
from .hypothesis import Hypothesis, TournamentResult
from .engine import TacticalHypothesisEngine
from ..security.security_barrier_policy import CommandAllowlistPolicy
from ..dtos.domain_dtos import AnalysisRequest, DomainAnalysisReport, CommandSpec, ChecklistTemplate

ALLOWED_FORENSICS_BINARIES: FrozenSet[str] = frozenset({
    "strings", "exiftool", "binwalk", "file", "sha256sum"
})


@register_solver("forensics")
@register_solver("stego")
class ForensicsDomainSolver(BaseDomainSolver):
    """Solver especializado em Forense Digital e Esteganografia com Engine de Torneio de Hipóteses."""

    def __init__(self, executor=None, file_reader=None, engine: TacticalHypothesisEngine = None):
        super().__init__(executor=executor, file_reader=file_reader)
        self.engine = engine or TacticalHypothesisEngine()
        self.security_policy = CommandAllowlistPolicy(ALLOWED_FORENSICS_BINARIES)

    @property
    def domain_type(self) -> str:
        return "forensics"

    def get_checklist(self, file_path: str = "evidence.file") -> List[ChecklistTemplate]:
        return [
            ChecklistTemplate(
                name="Metadata",
                human_readable_command=f"exiftool {file_path}",
                description="Extrai metadados EXIF/IPTC sem acionar shell."
            ),
            ChecklistTemplate(
                name="Embedded files",
                human_readable_command=f"binwalk {file_path}",
                description="Detecta arquivos embarcados por assinatura."
            ),
            ChecklistTemplate(
                name="Extract embedded",
                human_readable_command=f"binwalk -e {file_path}",
                description="Extrai arquivos embarcados para disco."
            ),
            ChecklistTemplate(
                name="File identification",
                human_readable_command=f"file {file_path}",
                description="Identifica o tipo de arquivo por magic bytes."
            ),
        ]

    def solve_tactical_step(self, metadata: Dict[str, Any]) -> TournamentResult[CommandSpec]:
        """Gera, sanitiza e ranqueia hipóteses táticas de forense via Torneio Elo."""
        target = str(metadata.get("target_resource", "evidence.file"))
        mime_type = str(metadata.get("mime_type", "")).lower()

        # Configura pontuações iniciais com base em heurística contextual
        hyp_file_score = 0.9 if "unknown" in mime_type or not mime_type else 0.5
        hyp_exif_score = 0.95 if "image" in mime_type or "jpeg" in mime_type or "png" in mime_type else 0.4
        hyp_binwalk_score = 0.9 if "zip" in mime_type or "octet-stream" in mime_type else 0.5
        hyp_strings_score = 0.7 if "text" in mime_type or "executable" in mime_type else 0.3
        hyp_sha256_score = 0.3

        hypotheses = [
            Hypothesis(
                id="hyp_file",
                name="Identificação por Magic Bytes",
                payload=CommandSpec(binary="file", args=[target]),
                initial_score=hyp_file_score,
            ),
            Hypothesis(
                id="hyp_exif",
                name="Análise de Metadados EXIF",
                payload=CommandSpec(binary="exiftool", args=[target]),
                initial_score=hyp_exif_score,
            ),
            Hypothesis(
                id="hyp_binwalk",
                name="Inspeção de Assinaturas de Arquivo Embarcado",
                payload=CommandSpec(binary="binwalk", args=[target]),
                initial_score=hyp_binwalk_score,
            ),
            Hypothesis(
                id="hyp_strings",
                name="Extração de Strings Imprimíveis",
                payload=CommandSpec(binary="strings", args=[target]),
                initial_score=hyp_strings_score,
            ),
            Hypothesis(
                id="hyp_sha256",
                name="Cálculo de Hash SHA-256",
                payload=CommandSpec(binary="sha256sum", args=[target]),
                initial_score=hyp_sha256_score,
            ),
        ]

        return self.engine.run_tournament(
            hypotheses, context=metadata, policy=self.security_policy
        )

    def analyze(self, request: AnalysisRequest) -> DomainAnalysisReport:
        metadata = dict(request.options)
        metadata["target_resource"] = request.target_resource
        if "mime_type" not in metadata:
            target_lower = request.target_resource.lower()
            if target_lower.endswith((".png", ".jpg", ".jpeg")):
                metadata["mime_type"] = "image/png"
            elif target_lower.endswith(".zip"):
                metadata["mime_type"] = "application/zip"

        tournament_res = self.solve_tactical_step(metadata)
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
