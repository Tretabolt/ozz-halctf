"""
Bounded Context: Forensics Domain Solver
Responsabilidade Única (SRP): Análise forense de arquivos, esteganografia e metadados.
"""
from typing import List, Dict

class ForensicsDomainSolver:
    """Solver especializado em Forense Digital e Esteganografia."""

    def get_checklist(self, file_path: str = "evidence.file") -> List[Dict[str, str]]:
        return [
            {"name": "Metadata", "command": f"exiftool {file_path} 2>/dev/null"},
            {"name": "Embedded files", "command": f"binwalk {file_path} 2>/dev/null"},
            {"name": "Extract embedded", "command": f"binwalk -e {file_path} 2>/dev/null"},
            {"name": "Png stego", "command": f"zsteg {file_path} 2>/dev/null"},
        ]
