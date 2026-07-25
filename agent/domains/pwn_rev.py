"""
Bounded Context: Pwn & Reverse Engineering Domain Solver
Responsabilidade Única (SRP): Análise estática segura de binários ELF/PE e payloads de exploração.

GARANTIA DE SEGURANÇA:
NUNCA utiliza 'ldd' em binários não confiáveis (previne RCE via ld-linux.so/DT_RPATH).
Utiliza exclusivamente ferramentas de análise estática sem execução (readelf, objdump, file, strings).
"""
from typing import List, Dict

class PwnRevDomainSolver:
    """Solver especializado em Engenharia Reversa e Binary Exploitation Seguro."""

    def get_checklist(self, binary_path: str = "target_bin") -> List[Dict[str, str]]:
        return [
            {"name": "File type", "command": f"file {binary_path}"},
            {"name": "Strings", "command": f"strings {binary_path} | grep -E 'flag|CTF|secret|pass'"},
            {"name": "Security controls", "command": f"checksec --file={binary_path} 2>/dev/null"},
            {"name": "Shared libraries (Static)", "command": f"readelf -d {binary_path} 2>/dev/null || objdump -p {binary_path} 2>/dev/null"},
            {"name": "Disassembly summary", "command": f"objdump -d {binary_path} | head -30 2>/dev/null"},
        ]
