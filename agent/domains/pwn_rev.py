"""
Bounded Context: Pwn & Reverse Engineering Domain Solver
Responsabilidade Única (SRP): Análise estática segura de binários ELF/PE e payloads de exploração.

GARANTIA DE SEGURANÇA:
NUNCA utiliza 'ldd' em binários não confiáveis (previne RCE via ld-linux.so/DT_RPATH).
Utiliza exclusivamente ferramentas de análise estática sem execução (readelf, objdump, file, strings).
"""
from typing import List, Dict
from .base import BaseDomainSolver
from .registry import register_solver
from ..dtos.domain_dtos import AnalysisRequest, DomainAnalysisReport, CommandSpec, TacticalStrategy

@register_solver("pwn")
@register_solver("rev")
class PwnRevDomainSolver(BaseDomainSolver):
    """Solver especializado em Engenharia Reversa e Binary Exploitation Seguro (sem ldd)."""

    @property
    def domain_type(self) -> str:
        return "pwn"

    def get_checklist(self, binary_path: str = "target_bin") -> List[Dict[str, str]]:
        return [
            {"name": "File type", "command": f"file {binary_path}"},
            {"name": "Strings", "command": f"strings {binary_path} | grep -E 'flag|CTF|secret|pass'"},
            {"name": "Security controls", "command": f"checksec --file={binary_path} 2>/dev/null"},
            {"name": "Shared libraries (Static)", "command": f"readelf -d {binary_path} 2>/dev/null || objdump -p {binary_path} 2>/dev/null"},
            {"name": "Disassembly summary", "command": f"objdump -d {binary_path} | head -30 2>/dev/null"},
        ]

    def evaluate_tactical_strategy(self, security_controls: Dict[str, bool]) -> TacticalStrategy:
        """Motor de regras de decisão de domínio tático baseado nos controles de segurança."""
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
        else:
            return TacticalStrategy(
                strategy_name="LEAK_CANARY_AND_ROP",
                target_vulnerability="Full Protections Enabled (Canary + PIE)",
                prerequisites=["canary_leak_primitive", "rop_gadgets"]
            )

    def analyze(self, request: AnalysisRequest) -> DomainAnalysisReport:
        spec = CommandSpec(binary="readelf", args=["-d", request.target_resource])
        exec_res = self.executor.execute(spec)
        errors = [exec_res.error] if exec_res.error else []
        return DomainAnalysisReport(
            domain=self.domain_type,
            success=exec_res.success,
            observations=[exec_res.output] if exec_res.success else [],
            errors=errors,
            metadata={"target": request.target_resource}
        )
