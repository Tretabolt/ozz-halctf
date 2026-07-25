# ADR Template — Architectural Decision Record

> **Como usar**: copie este arquivo, renomeie para `ADR-NNN-titulo.md`, preencha o frontmatter
> YAML **antes de escrever o corpo**, e rode `python scripts/check_adr.py docs/ADR-NNN-*.md`
> para validar os campos obrigatórios. O script rejeita frontmatter vazio ou com valor inválido.

---

## Frontmatter Obrigatório

```yaml
---
adr_id: "ADR-NNN"
title: ""
status: ""        # Draft | Approved | Deprecated | Superseded
date: ""          # YYYY-MM-DD
author: ""

# ═══════════════════════════════════════════════════════════════════
# CAMPOS DE PROCESSO — OBRIGATÓRIOS. CI rejeita se vazio ou inválido.
# ═══════════════════════════════════════════════════════════════════

# Q1 — Este ADR formaliza uma spec já fechada, ou está à frente de uma spec em rascunho?
# Valores válidos: CLOSED_SPEC | AHEAD_OF_DRAFT | NO_SPEC_DEPENDENCY
spec_dependency_status: ""

# Q2 — Se AHEAD_OF_DRAFT: qual spec, e qual é o gatilho concreto de revisão?
# Obrigatório quando spec_dependency_status == AHEAD_OF_DRAFT. Caso contrário: "N/A"
# Exemplo: "SPEC-003 fechar — revisar tupla X e agent/domains/"
spec_review_trigger: ""

# Q3 — O código que motivou este ADR foi escrito antes ou depois dele?
# Valores válidos: CODE_BEFORE_ADR | CODE_AFTER_ADR | CONCURRENT
# CODE_BEFORE_ADR não invalida o ADR, mas exige honestidade na seção de Contexto.
code_adr_order: ""
---
```

> **Por que YAML, não prosa?** Os três campos têm valores enumerados que um script pode
> verificar sem parsing semântico. `spec_dependency_status: ""` (vazio) é detectável em
> uma linha de grep ou num loop Python de 5 linhas — ver `scripts/check_adr.py`.

---

## Corpo do ADR

```markdown
# ADR-NNN: [Título]

**Status:** [Draft | Approved | Deprecated | Superseded]
**Data:** YYYY-MM-DD
**Contexto:** [Sistema/camada afetada]

---

## 1. Contexto e Problema

[Descreva o problema. Se `code_adr_order == CODE_BEFORE_ADR`, declare explicitamente
que o código existia antes deste ADR — não omita essa informação.]

---

## 2. Decisão Arquitetural

[Descreva a decisão tomada. Se `spec_dependency_status == AHEAD_OF_DRAFT`, declare
que a formalização é uma hipótese de trabalho, não uma spec fechada.]

---

## 3. Consequências

[Consequências reais — não infladas. Se uma afirmação depende de uma spec em rascunho,
diga "hipótese consistente com X" em vez de "formalmente correto".]

---

## 4. Dependências e Riscos

[Preencher sempre que spec_dependency_status != NO_SPEC_DEPENDENCY.
Incluir: qual spec, o que muda se ela fechar diferente, e quem deve ser notificado.]
```

---

## Exemplo Preenchido — ADR-002 Como Deveria Ter Sido Escrito

> Este é o próprio ADR-002, reescrito retroativamente com o template.
> As respostas honestas nos campos de processo teriam tornado a
> "Harmonia Taxonômica 100%" impossível de escrever — o frontmatter
> teria forçado o autor a declarar `CODE_BEFORE_ADR` e `AHEAD_OF_DRAFT`
> antes de redigir o corpo.

```yaml
---
adr_id: "ADR-002"
title: "Formalização dos DomainSolvers e TacticalStrategy no Espaço Executivo (𝒳)"
status: "Approved"
date: "2026-07-25"
author: "ozz-halctf team"

spec_dependency_status: "AHEAD_OF_DRAFT"
spec_review_trigger: "SPEC-003 fechar — revisar tupla X=(Ω,A,P,R,ΣDomainSolvers) e agent/domains/ antes de qualquer merge que toque esses módulos. Ver BACKLOG.md BL-002."
code_adr_order: "CODE_BEFORE_ADR"
---
```

```markdown
# ADR-002: Formalização dos DomainSolvers e TacticalStrategy no Espaço Executivo (𝒳)

**Status:** Approved
**Data:** 2026-07-25

---

## 1. Contexto e Problema

O `MANIFESTO-RECON-ADAPTER.md` restringe o ReconAdapter ao Espaço de Eventos E.
Componentes como `PwnRevDomainSolver` e `TacticalStrategy` realizam inteligência
de decisão tática — precisavam de enquadramento taxonômico explícito.

**Nota de processo (code_adr_order = CODE_BEFORE_ADR)**: os DomainSolvers foram
implementados nas releases v1.1.0–v1.3.0 antes deste ADR existir. Este documento
é uma racionalização post-hoc da alocação taxonômica, não um design prospectivo.

---

## 2. Decisão Arquitetural

Todos os DomainSolvers pertencem ao Espaço Executivo X(t).

**Nota de processo (spec_dependency_status = AHEAD_OF_DRAFT)**: a tupla local
X(t) = (Ω, A, P, R, ΣDomainSolvers) foi definida aqui para estruturar o código
existente. Ela é consistente com o espírito qualitativo do MNHI 3.5, mas SPEC-003
(spec-mãe de X) está em rascunho — esta formalização é uma hipótese de trabalho,
não uma spec fechada.

---

## 3. Consequências

- **Hipótese de Alocação Taxonômica**: toda peça tem alocação declarada,
  revisável quando SPEC-003 fechar.
- **Pureza de Domínio**: DomainSolvers não executam SO diretamente — delegam
  para ProcessExecutorPort. Esta invariante é implementada e testada.

---

## 4. Dependências e Riscos

| Dependência | Status | Gatilho de Revisão |
|---|---|---|
| SPEC-003 | Rascunho | Se fechar e redefinir X, revisar este ADR e agent/domains/ |

Ver BACKLOG.md BL-002 para rastreamento.
```

---

## O que o CI verifica

`python scripts/check_adr.py docs/ADR-*.md` valida:

| Check | Regra |
|---|---|
| Frontmatter presente | Arquivo começa com `---` |
| Campos obrigatórios preenchidos | `adr_id`, `status`, `spec_dependency_status`, `spec_review_trigger`, `code_adr_order` não vazios |
| `spec_dependency_status` válido | Deve ser `CLOSED_SPEC`, `AHEAD_OF_DRAFT` ou `NO_SPEC_DEPENDENCY` |
| `code_adr_order` válido | Deve ser `CODE_BEFORE_ADR`, `CODE_AFTER_ADR` ou `CONCURRENT` |
| `spec_review_trigger` preenchido | Se `spec_dependency_status == AHEAD_OF_DRAFT`, não pode ser `N/A` ou vazio |

Exit code 0 = todos os checks passaram. Exit code 1 = rejeita merge.
