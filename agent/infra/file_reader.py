"""Implementação Real de Infraestrutura: SafeFileReader (<= 70 LOC)"""
from pathlib import Path
from ..ports.file_reader import FileReaderPort

class SafeFileReader(FileReaderPort):
    """Adaptador de leitura de arquivos utilizando pathlib."""

    def read_header(self, path: str, n_bytes: int = 4) -> bytes:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"Arquivo regular não encontrado: {path}")
        with p.open("rb") as f:
            return f.read(n_bytes)

    def exists(self, path: str) -> bool:
        try:
            return Path(path).is_file()
        except Exception:
            return False
