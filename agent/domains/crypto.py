"""
Bounded Context: Crypto Domain Solver
Responsabilidade Única (SRP): De-hashing, rotinas de decodificação e análise de cifras.
"""
import base64
import urllib.parse
from typing import Dict, Any

class CryptoDomainSolver:
    """Solver especializado para desafios de Criptografia e Codificação."""

    def decode_string(self, payload: str) -> Dict[str, str]:
        results = {}
        # Base64
        try:
            results["base64"] = base64.b64decode(payload).decode("utf-8", errors="ignore")
        except Exception:
            pass
        # Hex
        try:
            results["hex"] = bytes.fromhex(payload).decode("utf-8", errors="ignore")
        except Exception:
            pass
        # URL
        try:
            results["url"] = urllib.parse.unquote(payload)
        except Exception:
            pass
        return results
