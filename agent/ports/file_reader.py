"""Porta de Infraestrutura: FileReaderPort (<= 70 LOC)"""
from abc import ABC, abstractmethod

class FileReaderPort(ABC):
    """Interface abstrata para leitura e verificação segura de arquivos no SO."""

    @abstractmethod
    def read_header(self, path: str, n_bytes: int = 4) -> bytes:
        """Lê os primeiros n_bytes do arquivo."""
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Verifica se o caminho existe e é arquivo regular."""
        pass


class MockFileReader(FileReaderPort):
    """Mock FileReader para testes unitários isolados em memória."""

    def __init__(self, exists_return: bool = True, header_return: bytes = b"\x7fELF"):
        self.exists_return = exists_return
        self.header_return = header_return

    def read_header(self, path: str, n_bytes: int = 4) -> bytes:
        if not self.exists_return:
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")
        return self.header_return[:n_bytes]

    def exists(self, path: str) -> bool:
        return self.exists_return
