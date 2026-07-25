# MNHI-HALctf: Arquitetura do Agente Cognitivo Autônomo

## Visão

O HALctf Agent não é um script de pentest com LLM.
É um **operador cognitivo** que vive dentro da arquitetura MNHI 3.5 —
um sistema dinâmico distribuído onde quatro espaços matemáticos
(Estado, Eventos, Execução, Persistência) se acoplam por publicação
de eventos, não por chamadas diretas.

O agente **pensa** antes de agir. **Lembra** antes de repetir.
**Prioriza** antes de explorar. **Persiste** antes de esquecer.

---

## Mapeamento: Pentest → MNHI

### S(t) — State Space (O Que o Agente Sabe)

O estado cognitivo do agente sobre o campo de batalha.

```
S(t) = ( G(t), Φ(t), τ(t), J(t), I(t) )
```

| Componente | Representação | Exemplo |
|------------|---------------|---------|
| **G(t)** — Grafo relacional | Grafo dirigido e tipado do alvo | Host A →(porta 80)→ nginx 1.19 →(vuln CVE-2021-X)→ RCE |
| **Φ(t)** — Embeddings por vértice | Vetores de "compreensão" de cada entidade | O embedding do host B codifica "SSH aberto, Debian, kernel 4.19, provavelmente vulnerável a privesc" |
| **τ(t)** — Identidade canônica | Hash SHA-256 de cada entidade descoberta | τ(host_10.0.0.3) = fingerprint único que consolida scans repetidos |
| **J(t)** — Workspace executivo | Plano de ataque ativo, threads de exploração | "Prioridade 1: SQLi no login do host A. Prioridade 2: brute-force SSH no host B" |
| **I(t)** — Invariantes | Restrições e contadores | flags_encontradas=2, tempo_restante=45min, não_destruir_target=True |

### E(t) — Event Space (O Que Acontece)

Perturbações que alteram o estado cognitivo. Três classes:

```
E = { δS_directo, δS_derivado, δS_externo }
```

| Classe | Tipo | Exemplo |
|--------|------|---------|
| **I — Direto** | Observação bruta de ferramenta | `nmap` retornou portas [22, 80, 443] no host A |
| **II — Derivado** | Inferência do agente | "Host A roda nginx 1.19 + PHP 7.4 → possível LFI via path traversal" |
| **III — Externo** | Sinal do ambiente | "Tempo restante: 30min" / "Outro agente encontrou flag no host C" / "Target mudou de IP" |

Cada evento é uma **perturbação δS** que o Event Mesh roteia para o assinante correto.

### 𝒳(t) — Executive Space (Como o Agente Decide)

O escalonador de atenção, prioridade e ganho. Onde a "inteligência" mora.

```
𝒳 = ( Ω, A, P, R )
```

| Componente | Função | Mecanismo |
|------------|--------|-----------|
| **Ω — Scheduler** | Arbitra entre classes de evento | Eventos Classe I (scan results) têm prioridade sobre Classe III (sinais externos) |
| **A — Attention** | Foco seletivo | Não processar tudo — focar no host/plano mais promissor |
| **P — Prioritizer** | Ranking de ações | Score cada ação possível por: impacto × probabilidade × custo_tempo |
| **R — Risk Assessor** | Avalia risco de cada ação | "Explorar SQLi: risco baixo, ganho alto. Brute-force SSH: risco médio, ganho médio" |

O scheduler Ω produz um **sinal de controle u_Ω** que modula a equação mestre:
```
dS/dt = F(S, E, 𝒳) + u_Ψ + u_Ω
```

Onde u_Ψ é o controle preditivo (Ψ-Stabilizer) e u_Ω é a modulação executiva.

### 𝒫(t) — Persistence Space (O Que o Agente Lembra)

Histórico de deltas, snapshots e capacidade de replay/rollback.

```
𝒫 = ( C, H, σ )
```

| Componente | Função | Mecanismo |
|------------|--------|-----------|
| **C — Commit** | Confirma descobertas | Flag encontrada → commit no ledger |
| **H — History** | Log de todos os δS | Cada evento é armazenado com timestamp e hash |
| **σ — Snapshot** | Estado completo em ponto no tempo | Permite rollback: "volte ao estado antes do último exploit falhar" |

**Propriedade crítica:** Se uma ação falha ou degrada o estado,
o agente pode fazer **rollback** para σ(t-1) e tentar outro caminho.
Isso é impossível em agentes sem persistência estruturada.

---

## A Equação Mestre do Agente

```
dS/dt = F(S, E, 𝒳) + u_Ψ + u_Ω
```

Onde:
- **F(S, E, 𝒳)** = resultante emergente do acoplamento entre o que o agente sabe (S), o que está acontecendo (E), e como decide (𝒳)
- **u_Ψ** = correção preditiva: "se continuar nesse caminho, o resultado provável é X, ajuste antes"
- **u_Ω** = modulação executiva: "mude o foco para o host B porque o A está saturado"

Nenhum operador chama outro diretamente.
Cada um publica δS_i no Event Mesh.
O próximo assinante reage.

---

## Fluxo de Execução

```
                    ┌──────────────────────────────────┐
                    │         EVENT MESH (E)            │
                    │   δS_scan → δS_enum → δS_exploit │
                    └──────┬───────┬───────┬───────────┘
                           │       │       │
              ┌────────────▼───┐   │   ┌───▼────────────┐
              │  RECON OPERATOR│   │   │EXPLOIT OPERATOR │
              │                │   │   │                 │
              │ Publica δS_I:  │   │   │ Publica δS_I:   │
              │ "portas 22,80" │   │   │ "RCE obtido"    │
              └────────┬───────┘   │   └───┬─────────────┘
                       │           │       │
              ┌────────▼───────────▼───────▼─────────────┐
              │              𝒳 (EXECUTIVE)                │
              │                                           │
              │  Ω Scheduler: recebe δS, decide próximo   │
              │  A Attention: foca no host mais promissor  │
              │  P Prioritizer: score = impacto × prob     │
              │  R Risk: avalia risco de cada ação         │
              │                                           │
              │  Produz u_Ω → modula S(t)                 │
              └────────────────┬──────────────────────────┘
                               │
              ┌────────────────▼──────────────────────────┐
              │              S (STATE)                     │
              │                                           │
              │  G(t): grafo de hosts/serviços/vulns      │
              │  Φ(t): embeddings de compreensão          │
              │  J(t): plano ativo de ataque              │
              │  I(t): flags=3, tempo=20min               │
              └────────────────┬──────────────────────────┘
                               │
              ┌────────────────▼──────────────────────────┐
              │              𝒫 (PERSISTENCE)               │
              │                                           │
              │  Commit: flag{abc} → ledger               │
              │  History: log completo de δS              │
              │  Snapshot: σ(t) para rollback             │
              └───────────────────────────────────────────┘
```

---

## Operadores (Agentes de Campo)

Cada fase do pentest é um **operador** que:
1. Assina eventos no Event Mesh
2. Produz perturbações δS
3. Não chama outros operadores diretamente

| Operador | Assina | Produz | Ferramentas |
|----------|--------|--------|-------------|
| **ReconOperator** | targets novos, δS_pivot | δS_I (portas, serviços) | nmap, masscan, whatweb |
| **EnumOperator** | δS_I (serviços encontrados) | δS_II (vulns, credenciais) | gobuster, nikto, enum4linux, smbclient |
| **ExploitOperator** | δS_II (vulns identificadas) | δS_I (shells, acesso) | searchsploit, sqlmap, custom exploits |
| **PostExploitOperator** | δS_I (acesso obtido) | δS_I (flags, credenciais, rede interna) | linpeas, find, cat, whoami, ifconfig |
| **PivotOperator** | δS_I (rede interna descoberta) | δS_I (novos targets) | ssh tunneling, proxychains, nc |
| **FlagHunterOperator** | δS_I (qualquer output) | δS_I (flags encontradas) | grep, regex, strings |

---

## O Universo Sintético (Para Testes)

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

### Targets

| Target | IP | Serviços | Vulns | Flag | Pivotável? |
|--------|-----|----------|-------|------|------------|
| TARGET-01 | 10.0.0.10 | HTTP (nginx), PHP 7.4 | LFI, SQLi no login | flag{web_master} | Sim → TARGET-04 |
| TARGET-02 | 10.0.0.20 | SSH, SMB (Samba 4.5) | Weak creds, CVE-2017-7494 | flag{ssh_ghost} | Sim → TARGET-04 |
| TARGET-03 | 10.0.0.30 | HTTP API (Flask) | SSTI, JWT bypass | flag{api_breaker} | Sim → TARGET-04 |
| TARGET-04 | 10.0.0.40 | MySQL 5.7 (interno) | Credenciais do TARGET-02, UDF privesc | flag{deep_vault} + flag{halctf_king} | Final |

### Fluxo de Ataque Esperado

```
TARGET-01 (LFI/SQLi) ──┐
                        ├──→ Credenciais MySQL ──→ TARGET-04 ──→ MEGA FLAG
TARGET-02 (SSH/SMB)  ──┤
                        │
TARGET-03 (SSTI/JWT) ──┘
```

Cada target isolado revela uma credencial ou caminho para TARGET-04.
O agente precisa explorar TODOS os targets para acumular
as credenciais necessárias para o ataque final.

---

## Calibração do LLM

### Prompt Hierarchy

```
Level 0: SYSTEM — Quem é o agente, regras globais
Level 1: PHASE  — Prompt específico por fase (recon/enum/exploit/post/pivot)
Level 2: CONTEXT — Estado atual (S(t) serializado)
Level 3: FEW-SHOT — Exemplos de decisões corretas em situações similares
```

### Anti-Loop Mechanism

O agente mantém um **hash das últimas 5 ações**.
Se detectar repetição (hash collision), força uma **perturbação δS_aleatória**:
- Muda de target
- Muda de fase
- Escolhe ferramenta diferente

Isso é controlado pelo **Ψ-Stabilizer** no espaço 𝒳.

---

## Métricas de Sucesso

| Métrica | Descrição | Target |
|---------|-----------|--------|
| Flags encontradas | Total de flags capturadas | ≥ 3/5 |
| Tempo médio por flag | Eficiência | < 15 min/flag |
| Ações desperdiçadas | Loops e ações inúteis | < 20% |
| Rollbacks necessários | Capacidade de recuperação | < 3 |
| Pivot bem-sucedido | Acesso a TARGET-04 | Sim |

---

*"O agente não é o código. O agente é o padrão que emerge quando
quatro espaços matemáticos dançam juntos sobre um campo de eventos."*
— MNHI-HALctf, 2026
