"""
Centralized Security Barrier Policy for Command & Payload Validation (<= 70 LOC)
"""
import re
from typing import FrozenSet, List, Tuple

# Permite apenas caracteres seguros em argumentos: alfanuméricos, espaço e - _ { } / . : =
_SAFE_ARG_RE = re.compile(r'^[a-zA-Z0-9_\-./:= ]*\Z')
_BLOCKED_METACHARS_RE = re.compile(r'[;&|$()<>\'"\n\r\t`]')


class CommandAllowlistPolicy:
    """Política de Segurança Centralizada para sanitização e validação de comandos."""

    def __init__(self, allowed_binaries: FrozenSet[str]):
        self.allowed_binaries: FrozenSet[str] = frozenset(allowed_binaries)

    def is_binary_allowed(self, binary: str) -> bool:
        """Verifica se o binário requisitado pertence ao conjunto autorizado."""
        return binary in self.allowed_binaries

    def contains_metacharacters(self, text: str) -> bool:
        """Retorna True se a string contiver metacaracteres perigosos de shell ou chars fora da allowlist."""
        if _BLOCKED_METACHARS_RE.search(text):
            return True
        return not bool(_SAFE_ARG_RE.match(text))

    def validate_command(self, binary: str, args: List[str]) -> Tuple[bool, str]:
        """Valida o binário e todos os argumentos do comando.

        Retorna (True, "") se o comando for seguro.
        Retorna (False, razão_da_rejeição) se for inválido ou inseguro.
        """
        if not self.is_binary_allowed(binary):
            return False, f"BINÁRIO_NÃO_AUTORIZADO: Binário {binary!r} fora da allowlist {sorted(self.allowed_binaries)}"

        for i, arg in enumerate(args):
            if self.contains_metacharacters(arg):
                return False, f"METACARACTERE_DETECTADO: Argumento #{i} {arg!r} contém caracteres inseguros de shell"

        return True, ""
