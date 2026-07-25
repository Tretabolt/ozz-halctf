# docs/BACKLOG.md — Lacunas Declaradas e Itens de Acompanhamento

> Este arquivo rastreia lacunas identificadas em auditoria de arquitetura.
> Cada item tem critério concreto de conclusão. "Declarada" não significa "aceitável indefinidamente".
> Atualizar status quando o item for resolvido ou descartado com justificativa explícita.

---

## BL-001 — Cobertura de testes para `agent/memory.py` (Espaço $\mathcal{P}$)

| Campo | Valor |
|---|---|
| **Severidade** | Alta |
| **Status** | **Fechado em 25/07/2026** — `tests/test_memory_persistence.py` |
| **Identificado em** | Auditoria de arquitetura — 25/07/2026 |
| **Referência** | `docs/MNHI-OZZ-MASTER-PLAN.md` §5 |

**Contexto**: `agent/memory.py` implementa o Espaço de Persistência $\mathcal{P}(t)$ — histórico
SQLite $H$, flags idempotentes $C$, snapshots e registro de torneios.

**Critério de conclusão** (4 testes satisfeitos em `tests/test_memory_persistence.py`):
1. Persistência e recuperação do histórico $H$ via SQLite entre instâncias distintas (OK).
2. Idempotência de $C$: registrar a mesma flag duas vezes não incrementa o contador (OK).
3. Snapshot $\sigma$ / `tournaments`: salvar e recuperar histórico do Torneio de Hipóteses (OK).
4. Suíte de testes automatizada dedicada cobrindo o ciclo de vida do SQLite (OK).

---

## BL-002 — ADR-002 depende de SPEC-003 (em rascunho)

| Campo | Valor |
|---|---|
| **Severidade** | Média |
| **Status** | Aberto |
| **Identificado em** | Auditoria de arquitetura — 25/07/2026 |
| **Referência** | `docs/ADR-002-EXECUTIVE-DOMAIN-SOLVERS.md` §4 |

**Contexto**: ADR-002 formaliza o Espaço Executivo $\mathcal{X}$ com tupla
$(\Omega, A, P, R, \sum\text{DomainSolvers})$. Esta tupla foi definida localmente — SPEC-003
(spec-mãe de $\mathcal{X}$) está listada como "Rascunho" no PDF do MNHI 3.5.
O código em `agent/domains/` e `agent/nedk.py::Executive` foi escrito antes do ADR,
não depois — o ADR é racionalização post-hoc, não design prospectivo.

**Critério de conclusão**: Quando SPEC-003 for fechada:
1. Comparar a definição formal de $\mathcal{X}$ com a tupla local do ADR-002.
2. Se divergirem: revisar ADR-002 e, se necessário, refatorar `agent/domains/` antes de merge.
3. Marcar ADR-002 §4 como "SPEC-003 fechada em [data] — verificado em [data]".

**Rastreamento**: qualquer PR tocando `agent/domains/` ou `agent/nedk.py::Executive` deve
referenciar este item e verificar se SPEC-003 foi fechada desde o último merge.

---

## BL-003 — Solvers stub sem motor de regras de domínio

| Campo | Valor |
|---|---|
| **Severidade** | Baixa |
| **Status** | **Fechado em 25/07/2026** — `TacticalHypothesisEngine` & CoScientist Solvers |
| **Identificado em** | Auditoria de arquitetura — 25/07/2026 |
| **Referência** | `docs/MNHI-OZZ-MASTER-PLAN.md` §2.3 |

**Contexto**: Todos os 4 solvers de domínio (`Forensics`, `Privesc`, `Web`, `Crypto`) foram
refatorados para integrar o **Motor Tático de Torneio de Hipóteses** (`TacticalHypothesisEngine`),
utilizando o algoritmo de ranqueamento Elo Pairwise simétrico, `CommandAllowlistPolicy` e
payloads parametrizados tipados `solve_tactical_step(metadata)`.

**Critério de conclusão por solver** (Satisfeitos em `tests/test_domain_solvers_tactical.py`):

| Solver | Motor de regras de hipóteses implementado | Status |
|---|---|---|
| `ForensicsDomainSolver` | Ranqueamento por MIME/magic bytes (`exiftool`, `binwalk`, `strings`, `file`, `sha256sum`). | **FECHADO** |
| `PrivescDomainSolver` | Priorização contextual por `user_level` (`sudo -l`, `find -perm -4000`, `id`, `uname -a`). | **FECHADO** |
| `WebDomainSolver` | Enumeração HTTP por `target_type` (`curl -I`, `robots.txt`, `OPTIONS`, `nmap`). | **FECHADO** |
| `CryptoDomainSolver` | Análise contextual por `data_format` (`base64 -d`, `xxd`, `openssl asn1parse`). | **FECHADO** |

**Prioridade sugerida**: Forensics → Privesc → Web → Crypto (frequência em CTFs).

**Risco se não resolvido**: OCP e auto-discovery funcionam corretamente, mas o agente
responde a 4 dos 5 domínios com dados estáticos — zero inteligência decisória.

---

## Como fechar um item

1. Implementar os critérios listados.
2. Adicionar testes que cobrem o critério (sem testes, o item não está fechado).
3. Atualizar o status aqui: `Aberto` → `Fechado em [data] — [commit hash]`.
4. Remover referências ao item nos documentos que o citavam, ou substituir por links ao commit.
