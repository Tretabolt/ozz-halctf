# MNHI-HALctf: Arquitetura do Agente Cognitivo Autônomo (MNHI 3.5)

## Visão

O HALctf Agent (**Ozz**) não é um script de pentest acoplado a um LLM.
É o **Neural Executive Dynamic Kernel (NEDK)** — um operador cognitivo de segurança ofensiva formalizado na arquitetura **MNHI 3.5**.
O sistema é dinâmico e distribuído, onde quatro espaços matemáticos
(Estado $S$, Eventos $E$, Execução $\mathcal{X}$, Persistência $\mathcal{P}$) se acoplam reativamente por publicação
de eventos via barramento (`EventMesh`), e não por chamadas diretas.

O agente **pensa** antes de agir. **Lembra** antes de repetir.
**Prioriza** antes de explorar. **Persiste** antes de esquecer.

---

## A Equação Mestre do Agente

$$\frac{dS}{dt} = F(S, E, \mathcal{X}) + u_\Psi + u_\Omega$$

Onde:
- **$F(S, E, \mathcal{X})$**: Resultante emergente do acoplamento entre o que o agente sabe ($S$), as perturbações do ambiente ($E$), e a modulação cognitiva ($\mathcal{X}$).
- **$u_\Psi$**: Correção preditiva do $\Psi$-Stabilizer (detecção de loops e injeção de perturbação anti-estagnação).
- **$u_\Omega$**: Sinal de controle executivo (foco em alvos e fases calculados pelo Scheduler $\Omega$).

---

## Mapeamento Formal dos 4 Espaços Matemáticos

### 1. $S(t)$ — State Space (O Que a Mente Sabe)

$$S(t) = ( G(t), \Phi(t), \tau(t), J(t), I(t) )$$

| Componente | Mapeamento no Código (`agent/nedk.py`) | Descrição |
|------------|-----------------------------------------|-----------|
| **$G(t)$** — Grafo relacional | `StateSpace.graph` | Grafo dirigido e tipado do alvo (hosts, portas, serviços, vulnerabilidades). |
| **$\Phi(t)$** — Contexto & Embeddings | `StateSpace.context` | Vetores de compreensão e embeddings contextuais dos alvos. |
| **$\tau(t)$** — Identidade Canônica | `StateSpace.canonical_hash()` | Hash SHA-256 determinístico via ordenação lexicográfica e remoção de volatilidade. |
| **$J(t)$** — Workspace Executivo | `StateSpace.workspace` | Plano ativo de ataque e threads de exploração em andamento. |
| **$I(t)$** — Invariantes | `StateSpace.invariants` | Restrições explícitas (`flags_found`, limites de tempo, integridade do sistema). |

### 2. $E(t)$ — Event Space (Barramento & Perturbações $\delta S$)

$$E = \{ \delta S_{\text{direto}}, \delta S_{\text{derivado}}, \delta S_{\text{externo}} \}$$

- **`EventMesh` (`agent/nedk.py`)**: Barramento de publicação/assinatura para perturbações $\delta S$.
  - **Classe I (Direto)**: Observações brutas de ferramentas (Nmap, Nikto, Web, Ingestão).
  - **Classe II (Derivado)**: Inferências do agente e descobertas táticas.
  - **Classe III (Externo)**: Sinais de ambiente (timeouts, limites de memória, sinais de parada).

#### Adaptador de Ingestão/Recon (Espaço $E$)
Implementado conforme o manifesto vinculado [`docs/MANIFESTO-RECON-ADAPTER.md`](file:///c:/Users/Daniel%20Palma/Downloads/mimoclaw_workspace%20(1)/halctf-repo/docs/MANIFESTO-RECON-ADAPTER.md):
- Pipeline de 7 estágios (`RequestValidator` $\rightarrow$ `ProcessInvoker` $\rightarrow$ `RawResultParser` $\rightarrow$ `DomainMapper (ACL)` $\rightarrow$ `Normalizer` $\rightarrow$ `CanonicalHasher` $\rightarrow$ `EventPublisher`).
- Garantia estrita de $\le 70$ LOC por módulo.
- Emissão de `EventClassI` diretamente para o `EventMesh`, populando $G(t)$ e $\tau(t)$ em tempo real.

### 3. $\mathcal{X}(t)$ — Executive Space (Tomada de Decisão & Regulagem)

$$\mathcal{X} = ( \Omega, A, P, R )$$

| Componente | Mapeamento (`agent/nedk.py`) | Mecanismo Cognitivo |
|------------|------------------------------|---------------------|
| **$\Omega$ — Scheduler** | `Executive.schedule()` | Seleciona o alvo com maior potencial de ganho tático. |
| **$A$ — Attention** | `Executive.attend()` | Define o foco da fase (recon, enum, exploit, pivot). |
| **$P$ — Prioritizer** | `Executive.prioritize()` | Ranqueia ações pelo score $\text{Impacto} \times (1 - \text{Risco})$. |
| **$R$ — Risk Assessor** | `Executive.assess_risk()` | Avalia o risco de detecção ou de quebrar o ambiente alvo. |

### 4. $\mathcal{P}(t)$ — Persistence Space (Persistência & Memória Tática)

$$\mathcal{P} = ( C, H, \sigma )$$

- **Commit ($C$)**: Registro idempotente de flags capturadas no ledger.
- **Histórico ($H$)**: Log estruturado de todas as observações no SQLite (`agent/memory.py`).
- **Snapshots ($\sigma$)**: Método `StateSpace.snapshot()` e `restore()` permitindo **rollback tático** em caso de falha de estratégia.

---

## Estrutura do Substrato Físico (E1 Layer / Docker)

A infraestrutura é projetada para garantir **alta disponibilidade e resiliência**:
- **Dual-Engine Server (`scripts/hf_server.py` + vLLM)**:
  - Se GPU com compute capability $\ge \text{sm\_75}$ estiver disponível $\rightarrow$ Inicializa **vLLM**.
  - Em GPUs mais antigas (Tesla P100 $\text{sm\_60}$) ou ambientes CPU $\rightarrow$ Chaveia automaticamente para **PyTorch Native FP16 / CPU FP32 fallback**.
- **Contrato OpenAI-API**: Barramento em `http://localhost:8000/v1/` 100% preservado.

---

## O Universo Sintético de Testes

### Topologia de Rede

```
┌─────────────────────────────────────────────────────────┐
│                    NETWORK: 10.0.0.0/24                  │
│                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │  TARGET-01   │    │  TARGET-02   │    │ TARGET-03  │ │
│  │  10.0.0.10   │    │  10.0.0.20   │    │ 10.0.0.30  │ │
│  │              │    │              │    │            │ │
│  │  Web Vuln    │    │  SSH + SMB   │    │  API REST  │ │
│  │  (DVWA-like) │    │  (Debian)    │    │  (custom)  │ │
│  │              │    │              │    │            │ │
│  │  flag{web_   │    │  flag{ssh_   │    │ flag{api_  │ │
│  │   master}    │    │   ghost}     │    │  breaker}  │ │
│  └──────┬───────┘    └──────┬───────┘    └─────┬──────┘ │
│         │                   │                   │        │
│         └───────────┬───────┘                   │        │
│                     │                           │        │
│              ┌──────▼───────┐                   │        │
│              │  TARGET-04   │◄──────────────────┘        │
│              │  10.0.0.40   │                            │
│              │              │                            │
│              │  Internal    │                            │
│              │  Database    │                            │
│              │  (MySQL)     │                            │
│              │              │                            │
│              │  flag{deep_  │                            │
│              │   vault}     │                            │
│              │              │                            │
│              │  + MEGA FLAG │                            │
│              │  flag{halctf_│                            │
│              │   king}      │                            │
│              └──────────────┘                            │
│                                                          │
│  ┌──────────────┐                                       │
│  │  OZZ AGENT   │                                       │
│  │  10.0.0.100  │                                       │
│  │  (Docker)    │                                       │
│  └──────────────┘                                       │
└─────────────────────────────────────────────────────────┘
```

---

## Validação e Qualidade (Suíte TDD de 30 Testes)

A integridade arquitetural é garantida por **30 testes automatizados** (100% PASS):

| Suíte de Testes | Quantidade | Escopo de Validação |
|------------------|------------|---------------------|
| `test_nedk.py` | 17 testes | Espaços $S$, $E$, $\mathcal{X}$, $\mathcal{P}$, $\Psi$-Stabilizer e NEDK. |
| `test_recon_adapter.py` | 3 testes | Contratos do manifesto, determinismo de $\tau$, ACL e limite de $\le 70$ LOC. |
| `test_nedk_recon_coupling.py` | 3 testes | Pub/Sub no `EventMesh` e atualização reativa do $G(t)$ e $\tau(t)$. |
| `test_docker_build.py` | 3 testes | Integridade do `Dockerfile`, `hf_server.py` e scripts de fallback. |
| `test_e2e_docker_compose.py` | 2 testes | Validação do `docker-compose.full.yml` e `mock_runner.py`. |
| `test_kaggle_deploy.py` | 2 testes | Especificações de GPU e metadados de execução remota. |

---

*"O agente não é o código. O agente é o padrão que emerge quando
quatro espaços matemáticos dançam juntos sobre um campo de eventos."*
— MNHI 3.5 / Ozz NEDK Kernel, 2026
