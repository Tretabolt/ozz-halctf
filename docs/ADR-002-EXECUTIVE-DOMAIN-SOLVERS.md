# ADR-002: Formalização dos DomainSolvers e TacticalStrategy no Espaço Executivo (𝒳)

**Status:** Aprovado  
**Data:** 25 de Julho de 2026  
**Contexto:** Arquitetura MNHI 3.5 — Integração da Inteligência Ofensiva ao Kernel NEDK  

---

## 1. Contexto e Problema

O manifesto [`MANIFESTO-RECON-ADAPTER.md`](file:///c:/Users/Daniel%20Palma/Downloads/mimoclaw_workspace%20(1)/halctf-repo/docs/MANIFESTO-RECON-ADAPTER.md) estabeleceu formalmente o adaptador de Recon/OSINT, restringindo seu escopo exclusivamente ao **Espaço de Eventos $E$** (coleta passiva/ativa de observações sem tomada de decisão ofensiva).

Entretanto, componentes como `PwnRevDomainSolver`, `WebDomainSolver`, `PrivescDomainSolver` e os objetos de valor `TacticalStrategy` realizam **inteligência de decisão tática e seleção de vetores de ataque** (ex: `RET2LIBC_STACK_OVERFLOW`, `LEAK_CANARY_AND_ROP`, `SHELLCODE_INJECTION`).

Para evitar a existência de "peças órfãs" fora da formalização matemática do MNHI 3.5, este ADR formaliza o enquadramento taxotômico de todos os `DomainSolvers`.

---

## 2. Decisão Arquitetural

1. **Enquadramento no Espaço Executivo $\mathcal{X}$**:
   Todos os `DomainSolvers` (`PwnRevDomainSolver`, `WebDomainSolver`, etc.) e seus motores de regras de decisão tática pertencem estritamente ao **Espaço Executivo $\mathcal{X}(t)$**, atuando como moduladores especializados dos operadores $\Omega$ (Scheduler), $A$ (Attention Focus) e $P$ (Prioritizer).

   $$\mathcal{X}(t) = \Big( \Omega(t), A(t), P(t), R(t), \sum \text{DomainSolvers} \Big)$$

2. **Separação Rígida entre $E$ e $\mathcal{X}$**:
   - **Espaço $E$ (ReconAdapter)**: Produz observações brutas e fatos do ambiente ($G(t)$, $\tau(t)$) sem julgar ou escolher ataques.
   - **Espaço $\mathcal{X}$ (DomainSolvers)**: Consome a fotografia de estado $S(t)$, avalia restrições táticas (ex: `NX`, `Canary`, `PIE`, `SUID`) e produz impulsos de controle $u_\Omega$ e DTOs `TacticalStrategy`.

3. **Invariante de Pureza de Domínio**:
   Nenhum `DomainSolver` em $\mathcal{X}$ executa comandos de SO diretamente. Toda interação de infraestrutura é delegada à porta `ProcessExecutorPort` em $E1$, garantindo que a regra de decisão tática seja 100% testável com mocks em memória.

---

## 3. Consequências

- **Harmonia Taxonômica 100%**: Toda peça do agente `ozz-halctf` pertence formalmente a um dos 4 espaços matemáticos ($S, E, \mathcal{X}, \mathcal{P}$). Zero peças órfãs.
- **Transparência de Limites**: O `MANIFESTO-RECON-ADAPTER.md` permanece intacto e focado no Espaço $E$, enquanto o `ADR-002` governa a inteligência ofensiva em $\mathcal{X}$.
