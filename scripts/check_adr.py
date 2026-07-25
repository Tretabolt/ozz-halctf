#!/usr/bin/env python3
"""
ADR Process Linter — valida campos obrigatórios de processo no frontmatter YAML dos ADRs.

Uso:
    python scripts/check_adr.py docs/ADR-*.md
    python scripts/check_adr.py docs/ADR-002-EXECUTIVE-DOMAIN-SOLVERS.md

Exit code 0: todos os checks passaram.
Exit code 1: campo ausente, vazio, ou valor inválido — rejeita merge.

Campos verificados:
    adr_id                  — obrigatório, não vazio
    status                  — obrigatório, não vazio
    spec_dependency_status  — CLOSED_SPEC | AHEAD_OF_DRAFT | NO_SPEC_DEPENDENCY
    spec_review_trigger     — obrigatório se spec_dependency_status == AHEAD_OF_DRAFT
    code_adr_order          — CODE_BEFORE_ADR | CODE_AFTER_ADR | CONCURRENT
"""
import re
import sys
from pathlib import Path

# ── Valores válidos por campo enumerado ──────────────────────────────────────
VALID_SPEC_STATUS = {"CLOSED_SPEC", "AHEAD_OF_DRAFT", "NO_SPEC_DEPENDENCY"}
VALID_CODE_ORDER  = {"CODE_BEFORE_ADR", "CODE_AFTER_ADR", "CONCURRENT"}

# Campos sempre obrigatórios (não vazios, não placeholder "")
REQUIRED_FIELDS = [
    "adr_id",
    "status",
    "spec_dependency_status",
    "spec_review_trigger",
    "code_adr_order",
]


def extract_frontmatter(text: str) -> dict | None:
    """Extrai pares chave:valor do frontmatter YAML (delimitado por ---).
    Ignora linhas de comentário (#) e retorna None se não houver frontmatter."""
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return None
    fm: dict[str, str] = {}
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or ":" not in stripped:
            continue
        key, _, val = stripped.partition(":")
        fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def check_adr(path: str) -> list[str]:
    """Retorna lista de mensagens de erro para um arquivo ADR.
    Lista vazia = arquivo válido. Nunca levanta exceção — erros viram mensagens."""
    errors: list[str] = []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (PermissionError, UnicodeDecodeError, OSError) as exc:
        return [f"[{path}] Não foi possível ler o arquivo: {exc}"]


    fm = extract_frontmatter(text)
    if fm is None:
        return [f"[{path}] Frontmatter YAML ausente — arquivo deve começar com ---"]

    # ── Check 1: campos obrigatórios não vazios ──────────────────────────────
    for field in REQUIRED_FIELDS:
        val = fm.get(field, "")
        if not val:
            errors.append(
                f"[{path}] Campo obrigatório '{field}' está vazio ou ausente"
            )

    # ── Check 2: spec_dependency_status deve ser valor enumerado ────────────
    spec_status = fm.get("spec_dependency_status", "")
    if spec_status and spec_status not in VALID_SPEC_STATUS:
        errors.append(
            f"[{path}] 'spec_dependency_status' = '{spec_status}' inválido. "
            f"Valores aceitos: {sorted(VALID_SPEC_STATUS)}"
        )

    # ── Check 3: AHEAD_OF_DRAFT exige spec_review_trigger preenchido ────────
    trigger = fm.get("spec_review_trigger", "")
    if spec_status == "AHEAD_OF_DRAFT" and (not trigger or trigger.upper() in ("N/A", "")):
        errors.append(
            f"[{path}] 'spec_review_trigger' não pode ser vazio ou N/A quando "
            f"spec_dependency_status == AHEAD_OF_DRAFT. "
            f"Descreva o gatilho concreto de revisão."
        )

    # ── Check 4: code_adr_order deve ser valor enumerado ────────────────────
    code_order = fm.get("code_adr_order", "")
    if code_order and code_order not in VALID_CODE_ORDER:
        errors.append(
            f"[{path}] 'code_adr_order' = '{code_order}' inválido. "
            f"Valores aceitos: {sorted(VALID_CODE_ORDER)}"
        )

    return errors


def main() -> int:
    paths = sys.argv[1:]
    if not paths:
        print("Uso: python scripts/check_adr.py docs/ADR-*.md")
        print("     Valida campos de processo obrigatórios no frontmatter YAML.")
        return 0

    all_errors: list[str] = []
    for path in paths:
        if not Path(path).exists():
            all_errors.append(f"[{path}] Arquivo não encontrado")
            continue
        all_errors.extend(check_adr(path))

    if all_errors:
        for err in all_errors:
            print(f"ERRO: {err}", file=sys.stderr)
        print(
            f"\n{len(all_errors)} erro(s) encontrado(s). "
            f"Corrija o frontmatter antes do merge.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: {len(paths)} ADR(s) passaram nos checks de processo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
