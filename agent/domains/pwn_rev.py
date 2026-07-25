"""
Bounded Context: Pwn & Reverse Engineering Domain Solver
Responsabilidade Única (SRP): Análise estática segura de binários ELF/PE e payloads de exploração.

GARANTIA DE SEGURANÇA:
NUNCA utiliza 'ldd' em binários não confiáveis (previne RCE via ld-linux.so/DT_RPATH).
Utiliza exclusivamente ferramentas de análise estática sem execução (readelf, objdump, file, strings).
"""
from dataclasses import dataclass
from typing import List, Dict
from .base import BaseDomainSolver
from .registry import register_solver
from ..dtos.domain_dtos import (
    AnalysisRequest, DomainAnalysisReport, CommandSpec,
    TacticalStrategy, ChecklistTemplate,
)


@dataclass(frozen=True)
class BinaryPath:
    """Value Object puro para validação sintática de caminhos de binários em memória.

    PREMISSA DE RUNTIME: O ambiente de produção do agente é Linux (container Docker / Kaggle).
    Ferramentas de análise estática (readelf, objdump) operam em ambiente POSIX.

    INVARIANTE: Zero I/O em __post_init__.
    Rejeita caminhos vazios, null bytes, path traversal ('..') e acessos a diretórios
    de sistema restritos POSIX (/etc/, /proc/, /sys/, /dev/), Windows e redes UNC.
    """
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("BinaryPath não pode ser vazio")
        if "\x00" in self.value:
            raise ValueError("Null byte injection detectada no caminho")

        normalized = self.value.replace("\\", "/")
        parts = [p for p in normalized.split("/") if p]
        if ".." in parts:
            raise ValueError(f"Path traversal detectado: {self.value!r}")

        if normalized.startswith("//") or self.value.startswith("\\\\"):
            raise ValueError(f"Acesso a caminho UNC de rede bloqueado: {self.value!r}")

        restricted_prefixes = (
            "/etc/", "/proc/", "/sys/", "/dev/", "/var/run/",
            "c:/windows/", "c:/winnt/", "c:/system32/"
        )
        norm_lower = normalized.lower()
        if any(norm_lower.startswith(prefix) for prefix in restricted_prefixes):
            raise ValueError(f"Acesso a caminho de sistema restrito bloqueado: {self.value!r}")


@register_solver("pwn")
@register_solver("rev")
class PwnRevDomainSolver(BaseDomainSolver):
    """Solver especializado em Engenharia Reversa e Binary Exploitation Seguro (sem ldd)."""

    @property
    def domain_type(self) -> str:
        return "pwn"

    def get_checklist(self, binary_path: str = "target_bin") -> List[ChecklistTemplate]:
        return [
            ChecklistTemplate(
                name="File type",
                human_readable_command=f"file {binary_path}",
                description="Detecta tipo ELF/PE/script. AVISO: libmagic faz mmap do binário."
            ),
            ChecklistTemplate(
                name="Strings",
                human_readable_command=f"strings {binary_path} | grep -E 'flag|CTF|secret|pass'",
                description="Template humano — contém '|'. NÃO executar via SafeProcessExecutor sem splitar."
            ),
            ChecklistTemplate(
                name="Security controls",
                human_readable_command=f"checksec --file={binary_path} 2>/dev/null",
                description="Detecta NX, Canary, PIE, RELRO."
            ),
            ChecklistTemplate(
                name="Shared libraries (Static)",
                human_readable_command=f"readelf -d {binary_path} 2>/dev/null",
                description="Análise estática sem acionar linker. Seguro."
            ),
            ChecklistTemplate(
                name="Disassembly summary",
                human_readable_command=f"objdump -d {binary_path} | head -30 2>/dev/null",
                description="Template humano — contém '|'. NÃO executar via SafeProcessExecutor sem splitar."
            ),
        ]

    def evaluate_tactical_strategy(self, security_controls: Dict[str, bool]) -> TacticalStrategy:
        """Motor de regras de decisão de domínio tático baseado nos controles de segurança.

        Cobre os 4 quadrantes da matriz de segurança (NX, Canary, PIE):
        - Quadrante 1: NX=False -> SHELLCODE_INJECTION
        - Quadrante 2: NX=True, Canary=False -> RET2LIBC_STACK_OVERFLOW
        - Quadrante 3: NX=True, Canary=True, PIE=False -> ROP_FIXED_BINARY_BASE
        - Quadrante 4: NX=True, Canary=True, PIE=True -> LEAK_CANARY_AND_ROP
        """
        nx = security_controls.get("NX", True)
        canary = security_controls.get("Canary", True)
        pie = security_controls.get("PIE", True)

        if not nx:
            return TacticalStrategy(
                strategy_name="SHELLCODE_INJECTION",
                target_vulnerability="Executable Stack (No NX)",
                prerequisites=["shellcode_payload", "buffer_offset"]
            )
        elif nx and not canary:
            return TacticalStrategy(
                strategy_name="RET2LIBC_STACK_OVERFLOW",
                target_vulnerability="Stack Buffer Overflow without Canary",
                prerequisites=["libc_base_leak", "system_address"]
            )
        elif nx and canary and not pie:
            return TacticalStrategy(
                strategy_name="ROP_FIXED_BINARY_BASE",
                target_vulnerability="Stack Protection with Fixed Binary Base (PIE disabled)",
                prerequisites=["canary_leak_primitive", "libc_leak_via_plt"]
            )
        else:
            return TacticalStrategy(
                strategy_name="LEAK_CANARY_AND_ROP",
                target_vulnerability="Full Protections Enabled (Canary + PIE)",
                prerequisites=["canary_leak_primitive", "rop_gadgets"]
            )

    def analyze(self, request: AnalysisRequest) -> DomainAnalysisReport:
        # 1. Validação Sintática de Domínio (Value Object em memória)
        try:
            target = BinaryPath(request.target_resource)
        except ValueError as exc:
            return DomainAnalysisReport(
                domain=self.domain_type,
                success=False,
                errors=[f"INVALID_TARGET: {exc}"],
                metadata={"target": request.target_resource}
            )

        # 2. Verificação de Existência via Porta FileReaderPort
        if not self.file_reader.exists(target.value):
            return DomainAnalysisReport(
                domain=self.domain_type,
                success=False,
                errors=[f"FILE_NOT_FOUND: Arquivo não encontrado: {target.value!r}"],
                metadata={"target": request.target_resource}
            )

        # 3. Verificação de Cabeçalho/Magic Bytes via Porta FileReaderPort
        try:
            header = self.file_reader.read_header(target.value, 4)
            if header != b"\x7fELF":
                return DomainAnalysisReport(
                    domain=self.domain_type,
                    success=False,
                    errors=[f"INVALID_FORMAT: Arquivo não é ELF (magic={header!r})"],
                    metadata={"target": request.target_resource}
                )
        except Exception as exc:
            return DomainAnalysisReport(
                domain=self.domain_type,
                success=False,
                errors=[f"READ_ERROR: Falha ao ler cabeçalho: {exc}"],
                metadata={"target": request.target_resource}
            )

        # 4. Execução de Análise via Porta ProcessExecutorPort
        spec = CommandSpec(binary="readelf", args=["-d", target.value])
        exec_res = self.executor.execute(spec)
        errors = [exec_res.error] if exec_res.error else []
        return DomainAnalysisReport(
            domain=self.domain_type,
            success=exec_res.success,
            observations=[exec_res.output] if exec_res.success else [],
            errors=errors,
            metadata={"target": request.target_resource}
        )
