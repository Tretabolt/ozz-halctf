# Plano Mestre do Agente Cognitivo Ozz (MNHI 3.5 — Release v1.4.1)

---

## 1. Visão Geral e Filosofia Arquitetural

O **Ozz (HALctf Agent)** é uma arquitetura de agente cognitivo autônomo orientada a eventos para segurança ofensiva. Baseia-se no **Neural Executive Dynamic Kernel (NEDK)** sob o paradigma **MNHI 3.5**.

A premissa mestre do projeto é **zero acoplamento direto entre espaços**: a mente do agente não
invoca ferramentas nem altera estados por chamadas síncronas entre espaços distintos; ela consome
perturbações do ambiente pelo barramento de eventos `EventMesh` e emite sinais de controle
executivos $u_\Omega$ e $u_\Psi$ — usados aqui como analogia semântica com a EDO mestre do
MNHI 3.5, não como implementação numérica dos termos da equação (ver ADR-002 §2 para os
limites desta formalização).

---

## 2. Mapeamento nos 4 Espaços Matemáticos

$$\frac{dS}{dt} = F(S, E, \mathcal{X}) + u_\Psi + u_\Omega$$

```text
               ┌────────────────────────────────────────┐
               │         S(t) — STATE SPACE             │
               │  Graph G(t), Hash τ(t), Invariants I(t) │
               └───────────────────▲────────────────────┘
                                   │  (State Update)
┌─────────────────────────┐        │        ┌─────────────────────────┐
│   E(t) — EVENT SPACE    ├────────┼───────►│  𝒳(t) — EXECUTIVE SPACE │
│ ReconAdapter, EventMesh │                │ DomainSolvers, Ω, A, P  │
└─────────────────────────┘                └────────────┬────────────┘
                                                        │ (Control Output)
                                           ┌────────────▼────────────┐
                                           │ P(t) — PERSISTENCE      │
                                           │ Snapshots σ, Flags C    │
                                           └─────────────────────────┘
```

### 2.1 Espaço de Estado $S(t)$ — `agent/nedk.py`
- **$G(t)$**: Grafo relacional dirigido do ambiente alvo (hosts, portas, serviços, vulnerabilidades).
- **$\tau(t)$**: Identidade canônica determinística do estado calculada por `CanonicalHasher`.
- **$I(t)$**: Restrições e contadores invariantes (`flags_found`, `max_memory`, `max_time`).

### 2.2 Espaço de Eventos $E(t)$ — `agent/recon_adapter/` & `agent/nedk.py`
- Governam a ingestão batch pelo pipeline de 7 estágios: `RequestValidator` $\rightarrow$ `ProcessInvoker` $\rightarrow$ `RawResultParser` $\rightarrow$ `DomainMapper (ACL)` $\rightarrow$ `Normalizer` $\rightarrow$ `CanonicalHasher` $\rightarrow$ `EventPublisher`.
- Emissão de perturbações $\delta S$ via `EventMesh` em 3 classes (Classe I: observações diretas; Classe II: inferências; Classe III: limites/erros).

### 2.3 Espaço Executivo $\mathcal{X}(t)$ — `agent/domains/` & `agent/nedk.py` (Formalizado via ADR-002)
- Contém o `Executive` ($\Omega$ Scheduler, $A$ Attention, $P$ Prioritizer, $R$ Risk Assessor)
e o `DomainSolverRegistry` com auto-discovery via `pkgutil` + `importlib` (OCP).

Domain Solvers — status por unidade:

| Solver | Status | Descrição |
|---|---|---|
| `PwnRevDomainSolver` | **IMPLEMENTADO** | Motor de decisão tática com 3 cenários de `TacticalStrategy` (NX/Canary/PIE). Integrado ao `SafeProcessExecutor` via `readelf -d` estático. |
| `ForensicsDomainSolver` | **STUB** | Interface e `ChecklistTemplate` implementados. Lógica de domínio pendente. |
| `WebDomainSolver` | **STUB** | `WebAttackTemplate` tipado. Motor de regras pendente. |
| `PrivescDomainSolver` | **STUB** | Checklists tipadas. Motor de regras pendente. |
| `CryptoDomainSolver` | **STUB** | Decode base64 básico. Pipeline de análise pendente. |

O mecanismo OCP está validado: `discover_solvers()` registra todos os 5 via `@register_solver`
sem alterar a Façade `ExploitArsenal`. Profundidade de implementação é desigual — ver
`docs/BACKLOG.md` item BL-003.

### 2.4 Espaço de Persistência $\mathcal{P}(t)$ — `agent/memory.py` & `agent/nedk.py`
- Histórico estruturado no SQLite $H$, registro idempotente de flags $C$ e snapshots de rollback $\sigma(t)$ para recuperar o estado do agente caso uma exploração falhe.

---

## 3. Diretrizes de Segurança, I/O e Isolamento (Ports & Adapters)

1. **Porta Abstrata de Infraestrutura (`ProcessExecutorPort`)**:
   - `agent/ports/executor.py`: Interface pura `execute(spec: CommandSpec) -> ExecutionResult`.
2. **Adaptador Seguro (`SafeProcessExecutor`)**:
   - `agent/infra/executor.py`: Chamadas via `subprocess.Popen(args, shell=False)` com lista de argumentos explícita (imunidade total a Command Injection RCE).
   - Consumo de buffers assíncrono via `proc.communicate(timeout)` prevenindo deadlocks em pipes de 64KB.
   - Encerramento forçado via `proc.kill()` (SIGKILL) em estouramento de timeout.
3. **Zero-Trust Static Analysis**:
   - Proibição estrita do `ldd`. Substituído por `readelf -d` estático sem acionamento de linkers dinâmicos do SO.

---

## 4. OCP e Auto-Discovery Dinâmico

- Novos solvers são adicionados decorando a classe com `@register_solver("domain_name")`.
- `DomainSolverRegistry.discover_solvers()` recarrega e descobre os solvers dinamicamente via `pkgutil` + `importlib` sem alterar uma única linha da Façade `ExploitArsenal`.

---

## 5. Mapeamento de Testes e Certificação TDD (56/56 PASS)

Cobertura por espaço MNHI:

| Espaço | Arquivos de Teste | Testes |
|---|---|---|
| $S$ (StateSpace) | `test_nedk.py` | 5 — graph, hash, flags, snapshot, rollback |
| $E$ (EventMesh + ReconAdapter) | `test_nedk.py`, `test_recon_adapter.py`, `test_nedk_recon_coupling.py` | ~16 |
| $\mathcal{X}$ (Executive + DomainSolvers) | `test_nedk.py`, `test_architecture_security.py`, `test_hexagonal_ocp.py`, `test_autodiscovery_deadlock_rules.py` | ~30 |
| Infraestrutura | `test_hexagonal_ocp.py`, `test_architecture_security.py` | ~5 |

> **⚠ LACUNA DECLARADA — Espaço $\mathcal{P}$ (`agent/memory.py`): ZERO cobertura de testes.**
> O módulo SQLite (histórico $H$, flags $C$, snapshots $\sigma$) não tem testes dedicados.
> `test_nedk.py::test_snapshot_and_rollback` testa `StateSpace` em memória — módulo distinto.
> **Risco**: rollback pode falhar silenciosamente durante sessão ativa de CTF.
> **Item de acompanhamento**: `docs/BACKLOG.md` — BL-001 (severidade: Alta).
