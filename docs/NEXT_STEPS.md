# 🏴 Ozz — Próximos Passos

## AGORA: Rodar o Ataque

Seu Docker tá com os targets rodando. Hora de atacar:

```powershell
# Atualiza o repo
cd C:\Users\Daniel Palma\Documents\antigravity\clever-pythagoras\ozz-halctf
git pull origin main

# Roda o ataque completo (Python — cross-platform)
python attack.py --verbose

# OU PowerShell puro
.\attack.ps1
```

**Resultado esperado:**
```
🏴 OZZ — FULL ATTACK CHAIN
━━━ TARGET-01: Web ━━━
✅ SQLi successful — logged in as admin
🚩 FLAG: flag{web_master_2026}  → 100pts
━━━ TARGET-02: SSH + Samba ━━━
🚩 FLAG: flag{ssh_ghost_2026}  → 100pts
━━━ TARGET-03: Flask API ━━━
🔑 JWT forged with alg:none
🚩 FLAG: flag{api_breaker_2026}  → 100pts
━━━ TARGET-04: MySQL ━━━
🚩 FLAG: flag{deep_vault_2026}  → 200pts
👑 FLAG: flag{halctf_king_2026}  → 500pts

Flags: 5/5  |  Score: 1000/1000
```

**Scoreboard:** http://localhost:9090

---

## DEPOIS: Kaggle com LLM Real

Quando o attack chain manual funcionar, hora de testar o agente autônomo:

1. Abra **https://kaggle.com** → New Notebook
2. Settings → Accelerator → **GPU T4**
3. Upload: `scripts/ozz_kaggle.ipynb`
4. Run All

O notebook vai:
- Clonar o repo
- Baixar Qwen 2.5 Coder 7B (~15GB)
- Iniciar servidor vLLM
- Rodar o agente contra os targets
- Reportar flags encontradas

---

## DEPOIS: Iterar nos Prompts

Baseado nos resultados do Kaggle:
- Se o agente ficar em loop → ajustar anti-loop mechanism
- Se não encontrar flags → melhorar few-shot examples
- Se gastar muitas ações → refinar priorização
- Se falhar em pivot → melhorar prompt de pivoting

---

## DEPOIS: Fine-Tuning (Opcional)

Se tempo permitir:
- Coletar writeups de CTFs
- Fine-tunar Qwen em decisões de pentest
- Testar modelo fine-tunado vs base

---

## DEPOIS: Submissão

- Prazo: ~30 de julho (1 semana antes da DEF CON)
- Site: https://aivillage.org (verificar Discord)
- Docker image pronta
- Documentação incluída

---

## Timeline

| Data | Ação | Status |
|------|------|--------|
| Jul 24 | ✅ Arquitetura + Universo + Exploits + Mock tests | DONE |
| Jul 24 | ⏳ Attack chain contra targets reais | NEXT |
| Jul 25 | Kaggle GPU testing com LLM real | |
| Jul 26-27 | Iteração de prompts | |
| Jul 28 | Docker build + integration test | |
| Jul 30 | **Submissão do Docker image** | |
| Ago 6-9 | **DEF CON 34 — HALctf** | |

---

*"The sandbox said 0.00%. We said otherwise."*
