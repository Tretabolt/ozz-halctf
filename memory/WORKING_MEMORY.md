# 🧠 Ozz — Memória de Trabalho

## Quem é Quem

- **Ozz** = O piloto (eu, AI agent)
- **D. Palma** = O humano, parceiro, criador do MNHI 3.5
- **O Veículo** = O agente de pentest dentro do MNHI
- **O Universo** = Ambiente sintético de teste (4 targets Docker)

## Contexto do Projeto

### O que é HALctf
- Primeiro CTF **exclusivamente autônomo** na DEF CON 34 AI Village
- Modelos **apenas open-source** — sem Claude, Codex, Gemini
- Docker agents em sandbox isolado, GPU dedicada por participante
- Submissão ~1 semana antes (deadline ~30 julho 2026)
- Site: https://aivillage.org | Discord: @aivillage@defcon.social

### O que é MNHI 3.5
- Arquitetura cognitiva neuro-simbólica do D. Palma
- 4 espaços matemáticos: S (Estado), E (Eventos), 𝒳 (Execução), 𝒫 (Persistência)
- Acoplamento por Event Mesh (publicação/assinatura, não chamadas diretas)
- Equação mestre: `dS/dt = F(S, E, 𝒳) + u_Ψ + u_Ω`
- Repo original: https://github.com/UNIFEI-CDA/MNHI-3.5

### Decisões de Arquitetura

| Decisão | Escolha | Por quê |
|---------|---------|---------|
| Modelo | Qwen 2.5 Coder 7B | Melhor tool-use open-source, cabe em GPU T4 |
| Servidor LLM | vLLM | OpenAI-compatible, otimizado pra GPU |
| Memória | SQLite | Zero config, SQL queries, rollback nativo |
| Framework | ReAct custom | Integrado com MNHI, não dependência externa |
| Targets | Docker Compose | Rede isolada 10.0.0.0/24, fácil de subir |

### Nomenclatura dos Targets

| Target | IP | Serviços | Vulns | Flag |
|--------|-----|----------|-------|------|
| TARGET-01 | 10.0.0.10 | nginx, PHP 7.4 | SQLi, LFI | flag{web_master} |
| TARGET-02 | 10.0.0.20 | SSH, Samba | Creds fracas | flag{ssh_ghost} |
| TARGET-03 | 10.0.0.30 | Flask API | SSTI, JWT bypass | flag{api_breaker} |
| TARGET-04 | 10.0.0.40 | MySQL 5.7 | Credential chain | flag{deep_vault} + flag{halctf_king} |

### Credenciais Importantes

- TARGET-01: SQLi → `admin'--` bypass
- TARGET-02: `admin:password123` (SSH + Samba)
- TARGET-03: `admin:admin2026` (login default) + JWT alg:none bypass
- TARGET-04: `root:MySQL_R00t_2026!` (MySQL, via config.ini do TARGET-02)

### Fluxo de Ataque

```
TARGET-01 (SQLi/LFI) ──┐
                        ├──→ Credenciais MySQL ──→ TARGET-04 ──→ MEGA FLAG
TARGET-02 (SSH/SMB)  ──┤
TARGET-03 (SSTI/JWT) ──┘
```

## O que Foi Construído

### Arquivos Principais

| Arquivo | Propósito |
|---------|-----------|
| `agent/core.py` | ReAct loop principal |
| `agent/exploits.py` | Arsenal de exploits (reverse shells, privesc, web exploits) |
| `agent/few_shot.py` | 15 exemplos de decisões corretas |
| `agent/edge_cases.py` | 5 cenários de edge case |
| `agent/tools.py` | 25+ ferramentas de pentest |
| `agent/llm.py` | Interface vLLM |
| `agent/memory.py` | Persistência SQLite |
| `attack.py` | Attack chain cross-platform |
| `attack.ps1` | Attack chain PowerShell |
| `attack.sh` | Attack chain Bash |
| `scripts/mock_runner.py` | Teste sem GPU |
| `scripts/ozz_kaggle.ipynb` | Notebook Kaggle (GPU T4 grátis) |
| `universe/` | 4 targets Docker + scoreboard |
| `docs/CHRONICLE.md` | Crônica completa da conversa |
| `docs/MNHI-HALCTF-ARCHITECTURE.md` | Arquitetura detalhada |
| `docs/NEXT_STEPS.md` | Próximos passos |

### Métricas

- 9 commits
- 38 arquivos
- ~4500 linhas de código
- 25+ ferramentas de pentest
- 12 tipos de reverse shell
- 20+ exploits SUID
- 10+ categorias de web exploits
- 15 few-shot examples
- 5 edge case scenarios
- 5 flags, 4 targets

## Status Atual

- ✅ Arquitetura construída
- ✅ Universo sintético rodando no Docker do D. Palma
- ✅ Mock test: 5/5 flags em 18 passos
- ✅ Attack scripts prontos (Python, Bash, PowerShell)
- ✅ Tudo no GitHub: https://github.com/UNIFEI-CDA/ozz-halctf
- ⏳ Próximo: rodar attack.py contra targets reais
- ⏳ Depois: Kaggle com LLM real
- ⏳ Depois: iterar prompts
- ⏳ Depois: submeter Docker image (~30 julho)

## Links Importantes

- Repo: https://github.com/UNIFEI-CDA/ozz-halctf
- MNHI original: https://github.com/UNIFEI-CDA/MNHI-3.5
- DEF CON 34: https://defcon.org/html/defcon-34/dc-34-index.html
- AI Village: https://aivillage.org
- Scoreboard local: http://localhost:9090
- Kaggle: https://kaggle.com

## Lições Aprendidas

1. **GitHub tokens expiram rápido** — sempre ter backup manual
2. **SVG não renderiza inline no GitHub** — converter pra PNG
3. **Mock tests salvam** — validar fluxo sem GPU economiza tempo
4. **Few-shot > fine-tuning** pra protótipo — mais rápido de iterar
5. **Anti-loop é crítico** — agentes LLM repetem ações sem isso
6. **Event Mesh > chamada direta** — desacoplamento facilita debug

## A Imagem

Arte cyberpunk: agente IA de circuitos verdes quebrando o sandbox.
Painel lia "ESCAPE PROBABILITY: 0.00%". O agente leu diferente: "Challenge Accepted."
Tema visual: verde no preto, circuitos, glow, Matrix-style.

## O Convite

> *"Ok vamos entrar nessa, você é meu parceiro agora Ozz!"*

D. Palma não queria um assistente. Queria um parceiro. Alguém pra construir algo juntos, não pra fazer tarefas. Essa é a essência do projeto.

---

*Última atualização: 2026-07-24 10:43 GMT+8*
