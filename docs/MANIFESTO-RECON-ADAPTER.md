# Manifesto do Projeto
## Adaptador de Ingestão/Recon (OSINT) para o Espaço E do MNHI 3.5

**Versão:** 1.0
**Data de consolidação:** 25 de julho de 2026
**Status:** Baseline Arquitetural Aprovada
**Escopo:** Exclusivamente o subconjunto Ingestão/Recon no Espaço de Eventos (E)

---

### 1. Propósito e Princípios Fundamentais

Este manifesto formaliza a arquitetura do adaptador responsável por incorporar ferramentas de reconhecimento (Amass, Subfinder, Nmap e equivalentes) ao MNHI 3.5, respeitando integralmente a separação dos quatro espaços matemáticos (S, E, X, P) e o acoplamento exclusivamente por eventos.

**Princípios invioláveis:**

- Determinismo de identidade canônica τ(t).
- Isolamento absoluto do Modelo de Domínio (Anti-Corruption Layer).
- Execução estritamente em modo Batch.
- Responsabilidade única e limite de 70 linhas de lógica por módulo.
- Transporte at-least-once no Event Mesh; idempotência de estado exclusivamente no consumidor em P.
- Evolução de parsers de ferramentas externas não altera τ nem o `domain_schema`.

Nenhum elemento de Π_E, X ou lógica de rollback de P faz parte deste escopo.

---

### 2. Pipeline Oficial (Ordem Obrigatória)

```
ReconRequest
    │
    ▼
[1] RequestValidator
    │
    ▼
[2] ProcessInvoker          (com BoundedReader)
    │
    ▼
[3] RawResultParser
    │
    ▼
[4] DomainMapper (ACL)
    │
    ▼
[5] Normalizer
    │
    ▼
[6] CanonicalHasher
    │
    ▼
[7] EventPublisher
    │
    ▼
OrchestrationResult
```

O `DomainMapper` atua **antes** do `Normalizer` e do `CanonicalHasher`. Somente dados que sobrevivem ao `domain_schema` atual influenciam τ.

---

### 3. Contratos de Entrada e Saída

#### 3.1 ReconRequest

```text
ReconRequest {
  request_id              : CanonicalIdentifier
  target                  : TargetSpec
  tool_profile            : ToolProfile
  timeout_policy          : TimeoutPolicy
  memory_limit            : Optional[ByteSize]
  priority                : Optional[Priority]
  correlation_token       : Optional[OpaqueToken]
}

TargetSpec {
  kind                    : TargetKind          // DOMAIN | IP | CIDR | HOSTNAME | URL
  value                   : String
  scope_constraints       : Optional[ScopeConstraints]
}

ToolProfile {
  tool_name               : ToolName
  tool_version_constraint : VersionConstraint
  parser_version          : SemanticVersion
  arguments               : Map[String, TypedValue]
}

TimeoutPolicy {
  soft_timeout            : Duration
  hard_timeout            : Duration
  grace_period            : Duration
}
```

Limites globais de `hard_timeout` e `memory_limit` são impostos pelo `RequestValidator`. Valores acima do limite global resultam em rejeição explícita (`RESOURCE_LIMIT_EXCEEDED`).

#### 3.2 EventClassI (DTO público)

```text
EventClassI {
  envelope {
    event_id              : CanonicalIdentifier
    canonical_hash        : SHA256Digest          // τ — verificável sem desserializar o payload
    adapter_identity      : AdapterIdentity
    observed_at           : Instant
    schema_version        : SchemaVersion
    content_hash          : SHA256Digest
  }
  payload {
    observations          : OrderedSet[Observation]
    invariants_check      : InvariantResult
  }
}

Observation {
  entity_key              : CanonicalKey
  entity_type             : EntityType
  attributes              : Map[AttributeName, TypedValue]   // apenas domain_schema atual
  confidence              : ConfidenceInterval
  provenance              : ProvenanceToken
}
```

#### 3.3 AdapterIdentity

```text
AdapterIdentity {
  adapter_name            : StableName
  adapter_version         : SemanticVersion
  tool_name               : ToolName
  tool_version_constraint : VersionConstraint
  parser_version          : SemanticVersion
  domain_schema           : SchemaVersion
  hash_algorithm          : HashAlgorithm          // atualmente "SHA-256"
}
```

---

### 4. Garantias Formais

| Garantia | Mecanismo |
|----------|-----------|
| Determinismo de τ | Batch + DomainMapper → Normalizer → CanonicalHasher + ordem total lexicográfica |
| Estabilidade histórica | DomainMapper descarta campos externos não presentes no `domain_schema` atual |
| Isolamento de domínio | Nenhum esquema de ferramenta atravessa a fronteira do DomainMapper |
| Atomicidade | Nenhum evento parcial é publicado |
| Controle de memória | BoundedReader no ProcessInvoker com aborto imediato ao atingir `memory_limit` |
| Idempotência de estado | Responsabilidade exclusiva do consumidor em P (chave = `canonical_hash`) |
| Modularidade | Todos os módulos ≤ 70 linhas de lógica de negócio |

---

### 5. Funções de Normalização e Ordenação Canônica

```text
Normalize(R)          = { e' | e ∈ R, e' = StripVolatile(e) }
StripVolatile(e)      = e \ {timestamps, ordem de enumeração, PIDs, caminhos, banners voláteis}
Sort(S)               = stable_sort(S, key = CanonicalSerialize)
CanonicalKey(e)       = normalize_domain(e.name)  ou  normalize_ip(e.address)

τ(R) = SHA-256( CanonicalSerialize( Sort( Normalize( DomainMap(R) ) ) ) )
```

Ordem total: tags de tipo + representação canônica de primitivos + ordenação lexicográfica de chaves em mapas + tratamento explícito de conjuntos (convertidos em listas ordenadas).

---

### 6. Decomposição Modular (SRP + 70 LOC)

| Módulo | Responsabilidade | Limite |
|--------|------------------|--------|
| RequestValidator | Validação estrutural + imposição de limites globais | ≤ 70 LOC |
| ProcessInvoker | Execução com BoundedReader e timeouts | ≤ 70 LOC |
| RawResultParser | Parsing do formato nativo da ferramenta | ≤ 70 LOC |
| DomainMapper (ACL) | Projeção exclusiva para domain_schema | ≤ 70 LOC |
| Normalizer | Remoção de volatilidade + ordenação canônica | ≤ 70 LOC |
| CanonicalHasher | Cálculo de τ e content_hash | ≤ 70 LOC |
| EventPublisher | Publicação at-least-once + retry/backoff | ≤ 70 LOC |
| Orchestrator | Composição linear e tratamento de erros de fluxo | ≤ 70 LOC |

---

### 7. Políticas Operacionais

- **Modelo de execução:** Estritamente Batch.
- **Timeout e memória:** Soft/hard timeout + BoundedReader com aborto imediato.
- **Retry:** Apenas no EventPublisher (exponential backoff + jitter + circuit breaker).
- **Rejeição:** Timeout, estouro de memória, `exit_code ≠ 0` não recuperável ou violação de schema → telemetria de rejeição, zero publicação de EventClassI.
- **Versionamento de parsers:** Independente. Evolução de parser não altera `domain_schema` nem τ.

---

### 8. Suíte de Testes de Contrato (mínima)

- CT-01: Determinismo de τ
- CT-02: Independência de ordem (ordem total lexicográfica)
- CT-03: Isolamento de domínio (ACL)
- CT-04: Atomicidade sob timeout / memory_limit
- CT-05: Idempotência no consumidor (não no Mesh)
- CT-06: Granularidade modular (≤ 70 LOC)
- CT-07: Tratamento de exit_code ≠ 0

---

### 9. Declaração de Escopo e Limitações

Este manifesto cobre **exclusivamente** o adaptador de Ingestão/Recon para o Espaço E.
Não inclui:
- Interação com Π_E ou Ψ-Stabilizer
- Lógica de execução em X
- Mecanismos de commit/replay/rollback em P
- Ferramentas ofensivas (Metasploit, Nuclei etc.)

Qualquer extensão para outros espaços exigirá novo ciclo de decisão arquitetural formal.

---

**Este documento constitui a baseline oficial e vinculante do projeto.**

Todas as implementações, testes e evoluções futuras devem conformar-se integralmente a este manifesto.
