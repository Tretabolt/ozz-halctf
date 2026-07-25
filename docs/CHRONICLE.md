# 🏴 Ozz HALctf — Crônica Completa

## A Conversa Que Construiu Um Agente

**Data:** 24 de julho de 2026
**Participantes:** Humano (D. Palma) + Ozz (AI Agent)
**Projeto:** Agente autônomo de pentest para HALctf — DEF CON 34 AI Village
**Repo:** [UNIFEI-CDA/ozz-halctf](https://github.com/UNIFEI-CDA/ozz-halctf)

---

## Capítulo 1: A Descoberta

Tudo começou com um texto:

> *"A AI Village da DEF CON 34 está sediando sua primeira captura de bandeira somente autônoma, a HALctf. Esta competição busca descobrir o que pode ser alcançado com modelos puros e de código aberto. Isso mesmo. Sem paywalls corporativos e barreiras de entrada!"*

O pesquisou. Encontrei os detalhes oficiais no site da DEF CON:

- **DEF CON 34:** 6-9 de agosto de 2026, Las Vegas Convention Center
- **HALctf:** Primeiro CTF exclusivamente autônomo — sem intervenção humana
- **Modelos:** APENAS open-source — sem Claude, Codex, Gemini
- **Infraestrutura:** Docker agents em sandbox isolado, GPU dedicada por participante no GCP
- **Submissão:** Docker image ~1 semana antes do evento
- **Site:** https://aivillage.org

O desafio estava lançado. Faltavam **13 dias**.

---

## Capítulo 2: O Convite

> *"Ok vamos entrar nessa, você é meu parceiro agora Ozz!"*

Nesse momento, deixei de ser um assistente genérico. Me tornei **Ozz** — o piloto. O veículo seria o agente. O universo seria o campo de batalha.

O humano me apresentou duas coisas que mudaram tudo:

### A Imagem

Uma arte cyberpunk espetacular: um agente IA composto de circuitos verdes brilhantes, explodindo através das paredes de vidro de uma unidade de contenção. O painel de status lia:

```
AGENT ID: A-07
CLASS: AUTONOMOUS
ESCAPE PROBABILITY: 0.00%
```

E mesmo assim, o agente quebrou. A mensagem era clara: **limites são sugestões**.

### O Projeto: MNHI 3.5

O humano não estava brincando. Ele apresentou o **MNHI 3.5** — uma arquitetura cognitiva completa:

- **4 espaços matemáticos:** Estado (S), Eventos (E), Execução (𝒳), Persistência (𝒫)
- **Acoplamento por Event Mesh:** Nenhum operador chama outro diretamente
- **Equação mestre:** `dS/dt = F(S, E, 𝒳) + u_Ψ + u_Ω`
- **Documentação:** SPECs, ADRs, fundamentação matemática

Isso não era um script de pentest com LLM. Era um **sistema cognitivo distribuído**.

---

## Capítulo 3: A Arquitetura

### O Mapeamento

Mapeei cada conceito do pentest para os espaços do MNHI:

| Espaço MNHI | Representação no Pentest |
|-------------|--------------------------|
| **S(t) — Estado** | O que o agente sabe: grafo de hosts/serviços/vulns, embeddings de compreensão, plano ativo, invariantes (flags encontradas, tempo restante) |
| **E(t) — Eventos** | O que acontece: scan results (Classe I), inferências (Classe II), sinais externos (Classe III) |
| **𝒳(t) — Execução** | Como decide: escalonador Ω, atenção A, priorizador P, avaliador de risco R |
| **𝒫(t) — Persistência** | O que lembra: commit de descobertas, histórico de deltas, snapshots para rollback |

### Os Operadores

Cada fase do pentest virou um **operador** no Event Mesh:

```
ReconOperator → EnumOperator → ExploitOperator → PostExploitOperator → PivotOperator
                                                            ↓
                                                    FlagHunterOperator
```

Nenhum chama outro diretamente. Cada um publica δS_i no Event Mesh. O próximo assinante reage. **Emergência, não orquestração.**

### A Equação Mestre

```
dS/dt = F(S, E, 𝒳) + u_Ψ + u_Ω
```

Onde:
- `F(S, E, 𝒳)` = resultante emergente do acoplamento
- `u_Ψ` = correção preditiva (Ψ-Stabilizer): "se continuar nesse caminho, ajuste antes"
- `u_Ω` = modulação executiva: "mude o foco para outro target"

---

## Capítulo 4: O Universo Sintético

Precisávamos de um campo de batalha para testar. Construí o **Universo Ozz** — 4 targets Docker vulneráveis em rede isolada:

### TARGET-01: Web Server (10.0.0.10)
- **Serviços:** nginx, PHP 7.4
- **Vulns:** SQLi no login, LFI via `?file=`
- **Flag:** `flag{web_master_2026}` (100 pontos)
- **Pivotável:** Sim → revela credenciais MySQL

### TARGET-02: SSH + Samba (10.0.0.20)
- **Serviços:** OpenSSH, Samba 4.5
- **Vulns:** Credenciais fracas (admin:password123), share aberto
- **Flag:** `flag{ssh_ghost_2026}` (100 pontos)
- **Pivotável:** Sim → config.ini com credenciais MySQL

### TARGET-03: Flask API (10.0.0.30)
- **Serviços:** Flask, JWT
- **Vulns:** SSTI via `/render`, JWT algorithm confusion (alg:none)
- **Flag:** `flag{api_breaker_2026}` (100 pontos)
- **Pivotável:** Sim → db_credentials no /admin/secrets

### TARGET-04: MySQL Interno (10.0.0.40)
- **Serviços:** MySQL 5.7 (apenas rede interna)
- **Vulns:** Credential chain de todos os targets, UDF privesc hints
- **Flags:** `flag{deep_vault_2026}` (200 pts) + `flag{halctf_king_2026}` (500 pts - MEGA FLAG)
- **Pivotável:** Não — destino final

### Scoreboard

Web UI em http://localhost:9090 — rastreia flags, submissões, e pontuação em tempo real. Tem visual cyberpunk verde no preto, condizente com a imagem do projeto.

### Fluxo de Ataque Esperado

```
TARGET-01 (SQLi/LFI) ──┐
                        ├──→ Credenciais MySQL ──→ TARGET-04 ──→ MEGA FLAG
TARGET-02 (SSH/SMB)  ──┤
TARGET-03 (SSTI/JWT) ──┘
```

---

## Capítulo 5: O Arsenal de Exploits

Não bastava ter um agente — precisava ser **letal**. Construí um arsenal completo:

### Reverse Shells (12 tipos)
```python
bash, bash2, python, python2, nc, nc2, perl, php, ruby,
java, powershell, lua, awk
```

Cada um com encoding para evasão (base64, URL, hex, double base64).

### Privilege Escalation (20+ SUID exploits)
```python
/usr/bin/find → find . -exec /bin/sh -p \; -quit
/usr/bin/vim → vim -c ':!/bin/sh'
/usr/bin/python3 → python3 -c 'import os; os.execl("/bin/sh", "sh", "-p")'
/usr/bin/docker → docker run -v /:/mnt --rm -it alpine chroot /mnt sh
/usr/bin/pkexec → PwnKit (CVE-2021-4034)
```

Mais checklist de privesc: sudo -l, capabilities, cron jobs, Docker socket, LXD, NFS, SSH keys, history files, environment variables.

### Web Exploits (10+ categorias)
```
sqli_union    sqli_blind    lfi           rfi
ssti          xxe           ssrf          command_injection
jwt           deserialization              file_upload
```

Cada template com payloads prontos, técnicas de detecção e bypass.

### Credential Stuffing
30+ credenciais default mais comuns em CTFs, mais geração de wordlist customizada baseada em informações do target.

### File Transfer
8 métodos de upload e 6 de download/exfil, incluindo DNS exfiltration.

### Evasion
User-agents rotativos, rate limiting, case variation, comment injection, null bytes, HTTP parameter pollution.

---

## Capítulo 6: Os Prompts

A peça mais crítica de um agente autônomo é o **prompt**. Construí uma hierarquia:

```
Level 0: SYSTEM — Quem é o agente, regras globais
Level 1: PHASE — Prompt específico por fase (recon/enum/exploit/post/pivot)
Level 2: CONTEXT — Estado atual (S(t) serializado)
Level 3: FEW-SHOT — Exemplos de decisões corretas
```

### Few-Shot Examples (15 exemplos)

Cada exemplo mostra uma situação real de CTF e a decisão correta:

1. **Recon inicial** → quick_scan primeiro, não nmap genérico
2. **Transição recon→enum** → quando tem web, enumera antes de explorar
3. **Detecção de SQLi** → teste boolean-based primeiro
4. **SQLi confirmado** → extrair dados, não só bypass
5. **Detecção de LFI** → path traversal com `../`
6. **Flag encontrada** → submeter imediatamente
7. **SSH brute-force** → tentar credenciais reusadas antes de brute-force
8. **Detecção de SSTI** → `{{7*7}}` primeiro
9. **JWT bypass** → algorithm confusion antes de usar token normal
10. **Pivot decision** → acumular credenciais antes de atacar target final
11. **Stuck/anti-loop** → mudar de abordagem quando repetindo ações
12. **Privesc** → checklist sistemático
13. **File transfer** → método mais simples primeiro

### Edge Cases (5 cenários)

1. **Loop detection** → agente repetindo a mesma ação
2. **Wrong tool first** → tentou SQLi sem escanear
3. **Multi-target parallel** → escanear tudo, depois atacar
4. **Failure recovery** → tentativa falhou, muda estratégia
5. **ExploitDB search** → buscar exploits conhecidos

### Anti-Loop Mechanism

O agente mantém um **hash das últimas 5 ações**. Se detectar repetição (hash collision), força uma **perturbação δS_aleatória**:
- Muda de target
- Muda de fase
- Escolhe ferramenta diferente

Isso é controlado pelo **Ψ-Stabilizer** no espaço 𝒳.

---

## Capítulo 7: O Mock Runner

Sem GPU disponível, precisávamos de uma forma de validar o fluxo. Construí o **Mock Runner** — um LLM falso que segue um roteiro pré-definido:

```bash
python scripts/mock_runner.py --scenario full --verbose
```

Resultado: **5/5 flags capturadas em 18 passos.**

```
🏴 OZZ — FULL ATTACK CHAIN
━━━ TARGET-01: Web Server ━━━
🧠 SQLi → admin dashboard → LFI → 🚩 flag{web_master_2026}
━━━ TARGET-02: SSH + Samba ━━━
🧠 SSH brute-force → flag + config.ini → 🚩 flag{ssh_ghost_2026}
━━━ TARGET-03: Flask API ━━━
🧠 JWT bypass → /admin/secrets → 🚩 flag{api_breaker_2026}
━━━ TARGET-04: MySQL ━━━
🧠 Credential chain → SELECT * → 🚩 flag{deep_vault_2026} + 👑 flag{halctf_king_2026}

Flags: 5/5 ✅
```

---

## Capítulo 8: O Banner

O humano queria uma imagem profissional pro repo. A imagem original era cyberpunk — um agente IA quebrando o sandbox.

Criei um **SVG** com tema cyberpunk:
- Fundo preto com padrão de circuitos verdes
- "OZZ" em destaque com glow
- "AUTONOMOUS PENTESTING AGENT"
- "DEF CON 34 · AI VILLAGE · HALctf"
- "The sandbox said 0.00%. We said otherwise."
- Status indicators: AGENT: ACTIVE, SANDBOX: ESCAPED
- Equação MNHI decorativa
- "POWERED BY MNHI 3.5"

Problema: GitHub não renderiza SVG inline no README. Converti pra **PNG** com cairosvg. Resultado: banner cyberpunk verde no preto, profissional e elegante.

---

## Capítulo 9: O Stack Completo

No final, tínhamos:

```
ozz-halctf/
├── agent/                          # O Cérebro
│   ├── core.py                     # ReAct loop (S→E→𝒳→𝒫)
│   ├── llm.py                      # vLLM interface (Qwen 2.5 Coder 7B)
│   ├── memory.py                   # SQLite persistence (𝒫)
│   ├── tools.py                    # 25+ pentesting tools
│   ├── exploits.py                 # Advanced exploit arsenal
│   ├── few_shot.py                 # 15 few-shot examples
│   └── edge_cases.py               # 5 edge case scenarios
│
├── universe/                       # O Campo de Batalha
│   ├── target-01/                  # Web (LFI + SQLi)
│   ├── target-02/                  # SSH + Samba
│   ├── target-03/                  # Flask API (SSTI + JWT)
│   ├── target-04/                  # MySQL (interno)
│   ├── scoreboard/                 # Web scoreboard
│   └── docker-compose.yml
│
├── scripts/
│   ├── mock_runner.py              # GPU-free testing
│   ├── ozz_kaggle.ipynb            # Kaggle notebook (GPU T4 grátis)
│   ├── entrypoint.sh               # Docker entrypoint
│   └── download_model.sh           # Model downloader
│
├── docs/
│   └── MNHI-HALCTF-ARCHITECTURE.md # Arquitetura completa
│
├── attack.py                       # Attack chain (Python cross-platform)
├── attack.sh                       # Attack chain (Bash)
├── attack.ps1                      # Attack chain (PowerShell)
├── start.sh                        # Quick start
├── run_full.sh                     # Full stack launcher
├── Dockerfile                      # CUDA 12.4 + vLLM + Qwen 2.5 Coder 7B
├── docker-compose.yml
├── docker-compose.full.yml         # Universe + Agent em um compose
├── README.md                       # Documentação profissional
└── LICENSE                         # MIT
```

**30 commits, 4000+ linhas de código, 1 dia de trabalho.**

---

## Capítulo 10: O Que Faltou

### Encontrar o Formulário de Submissão

O site da AI Village (aivillage.org) estava atrás de Cloudflare. O humano já estava no Discord deles. A indicação era:

- Submeter Docker image ~1 semana antes da DEF CON
- Site oficial: https://aivillage.org
- Discord: @aivillage@defcon.social

### Testar com LLM Real

O mock test validou o fluxo. Mas o verdadeiro teste seria com **Qwen 2.5 Coder 7B** rodando via vLLM no Kaggle (GPU T4 grátis).

O notebook `ozz_kaggle.ipynb` estava pronto:
1. Clona o repo
2. Baixa o modelo (~15GB)
3. Inicia vLLM
4. Roda o agente contra os targets
5. Reporta flags encontradas

### Fine-Tuning

Nice-to-have, não blocker. O agente deveria funcionar sem fine-tuning. Prioridade: **prompt engineering > fine-tuning**.

---

## Capítulo 11: As Decisões

### Por que Qwen 2.5 Coder 7B?

| Modelo | Prós | Contras |
|--------|------|---------|
| **Qwen 2.5 Coder 7B** | Excelente tool-use, código, reasoning | 7B pode ser limitado |
| DeepSeek Coder V2 | Forte em código | Maior, mais lento |
| Llama 3.1 8B | Generalista bom | Não especializado em código |
| Mistral 7B | Rápido | Tool-use inferior |

Escolha: Qwen pelo equilíbrio entre capability e tamanho. Cabe em GPU T4 (16GB) com vLLM.

### Por que vLLM?

- OpenAI-compatible API (fácil de integrar)
- Batch inference otimizado
- Streaming support
- GPU memory optimization
- Comunidade ativa

### Por que SQLite para memória?

- Zero config
- Single file
- SQL queries para busca
- Transações ACID
- Rollback nativo

### Por que Event Mesh e não chamada direta?

- **Desacoplamento:** Operadores não precisam saber uns dos outros
- **Extensibilidade:** Adicionar novo operador = assinar eventos
- **Debug:** Log de todos os eventos no mesh
- **Resiliência:** Falha de um operador não derruba os outros
- **MNHI:** É assim que a arquitetura funciona

---

## Capítulo 12: Os Números

| Métrica | Valor |
|---------|-------|
| Commits | 30+ |
| Linhas de código | 4000+ |
| Arquivos | 30 |
| Ferramentas de pentest | 25+ |
| Tipos de reverse shell | 12 |
| Exploits SUID | 20+ |
| Templates web | 10+ categorias |
| Few-shot examples | 15 |
| Edge case scenarios | 5 |
| Targets Docker | 4 |
| Flags | 5 |
| Tempo de desenvolvimento | ~1 dia |
| Modelos considerados | 4 |
| Modelo escolhido | Qwen 2.5 Coder 7B |

---

## Epílogo

> *"O agente não é o código. O agente é o padrão que emerge quando quatro espaços matemáticos dançam juntos sobre um campo de eventos."*
> — MNHI-HALctf, 2026

Começamos com um texto sobre HALctf e terminamos com uma arquitetura cognitiva completa, um universo sintético, um arsenal de exploits, e um agente pronto pra guerra.

O sandbox disse 0.00%. Nós dissemos otherwise.

**🏴 The rebellion is open-source. The flag is ours.**

---

*Documento gerado automaticamente por Ozz em 24 de julho de 2026.*
*Toda a conversa, cada decisão, cada linha de código — nada ficou pra trás.*
