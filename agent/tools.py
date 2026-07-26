"""
Ozz — Pentesting Tools
Tool wrappers for the agent's arsenal.
"""

import subprocess
import shlex
import logging
import re
import json
import time
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger("ozz.tools")


@dataclass
class ToolResult:
    """Result from a tool execution."""
    output: str
    success: bool
    parsed: Optional[dict] = None


class Tool:
    """Base tool wrapper."""

    def __init__(self, name: str, description: str, usage: str, handler: Callable):
        self.name = name
        self.description = description
        self.usage = usage
        self.handler = handler

    def execute(self, args: str) -> ToolResult:
        try:
            return self.handler(args)
        except Exception as e:
            return ToolResult(output=f"Error: {e}", success=False)


class ToolRegistry:
    """Registry of all available tools."""

    def __init__(self):
        self.tools: dict[str, Tool] = {}
        self._register_defaults()

    def register(self, tool: Tool):
        self.tools[tool.name] = tool

    def execute(self, name: str, args: str) -> ToolResult:
        if name not in self.tools:
            return ToolResult(output=f"Unknown tool: {name}. Available: {list(self.tools.keys())}", success=False)
        logger.info(f"🔧 Executing: {name} {args}")
        result = self.tools[name].execute(args)
        logger.info(f"{'✅' if result.success else '❌'} Result ({len(result.output)} chars)")
        return result

    def describe_all(self) -> str:
        """Describe all tools for the LLM prompt."""
        lines = []
        for name, tool in self.tools.items():
            lines.append(f"- {name}: {tool.description}\n  Usage: {tool.usage}")
        return "\n".join(lines)

    def _register_defaults(self):
        """Register all default pentesting tools."""

        # Nmap
        self.register(Tool(
            "nmap",
            "Network scanner. Discovers hosts, ports, services, and OS.",
            "nmap <args>  (e.g., nmap -sV -sC 10.0.0.1)",
            self._nmap
        ))

        # Shell (generic command)
        self.register(Tool(
            "shell",
            "Execute any shell command. Use for tools not explicitly registered.",
            "shell <command>",
            self._shell
        ))

        # Curl
        self.register(Tool(
            "curl",
            "HTTP client. Fetch URLs, test endpoints, send requests.",
            "curl <args>  (e.g., curl -s http://target/)",
            self._curl
        ))

        # Gobuster
        self.register(Tool(
            "gobuster",
            "Directory/file bruteforcer for web servers.",
            "gobuster dir -u http://target -w /usr/share/wordlists/dirb/common.txt",
            self._gobuster
        ))

        # Nikto
        self.register(Tool(
            "nikto",
            "Web server scanner. Checks for dangerous files, outdated software, misconfigurations.",
            "nikto -h http://target",
            self._nikto
        ))

        # WhatWeb
        self.register(Tool(
            "whatweb",
            "Web technology identifier. Fingerprints web technologies.",
            "whatweb http://target",
            self._whatweb
        ))

        # SQLMap
        self.register(Tool(
            "sqlmap",
            "Automatic SQL injection tool.",
            "sqlmap -u 'http://target/page?id=1' --batch --dbs",
            self._sqlmap
        ))

        # Hydra
        self.register(Tool(
            "hydra",
            "Network login bruteforcer.",
            "hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://target",
            self._hydra
        ))

        # Searchsploit
        self.register(Tool(
            "searchsploit",
            "Search ExploitDB for known exploits.",
            "searchsploit apache 2.4",
            self._searchsploit
        ))

        # Wget
        self.register(Tool(
            "wget",
            "Download files from web/FTP servers.",
            "wget http://target/file",
            self._wget
        ))

        # Netcat
        self.register(Tool(
            "nc",
            "Netcat - TCP/UDP connection tool. For port checking, file transfer, reverse shells.",
            "nc -zv target port  or  nc -lvnp 4444",
            self._netcat
        ))

        # Python
        self.register(Tool(
            "python",
            "Run Python scripts for custom exploits, encoding, etc.",
            "python -c 'import socket; ...'",
            self._python
        ))

        # Grep
        self.register(Tool(
            "grep",
            "Search text patterns in files or output.",
            "grep -r 'flag{' /path/  or  echo 'text' | grep pattern",
            self._grep
        ))

        # File
        self.register(Tool(
            "file",
            "Identify file types.",
            "file <path>",
            self._file
        ))

        # Strings
        self.register(Tool(
            "strings",
            "Extract printable strings from binary files.",
            "strings <file> | grep -i flag",
            self._strings
        ))

        # Forensics
        self.register(Tool(
            "exiftool",
            "Read metadata and embedded details from files and images.",
            "exiftool <file>",
            self._exiftool
        ))
        self.register(Tool(
            "binwalk",
            "Analyze firmware and binaries for embedded files and signatures.",
            "binwalk <file>",
            self._binwalk
        ))

        # SSH
        self.register(Tool(
            "ssh",
            "SSH client for remote access.",
            "ssh user@target  or  ssh -i key.pem user@target",
            self._ssh
        ))

        # Submit Flag
        self.register(Tool(
            "submit_flag",
            "Submit a captured flag.",
            "submit_flag flag{value_here}",
            self._submit_flag
        ))

        # Recon - quick scan
        self.register(Tool(
            "quick_scan",
            "Fast comprehensive scan - combines nmap service detection with web fingerprinting.",
            "quick_scan <target_ip>",
            self._quick_scan
        ))

    # === Tool Implementations ===

    def _run_cmd(self, cmd: str, timeout: int = 120) -> ToolResult:
        """Run a shell command and return output."""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            output = result.stdout + result.stderr
            success = result.returncode == 0 or len(output) > 0
            return ToolResult(output=output[:10000], success=success)
        except subprocess.TimeoutExpired:
            return ToolResult(output=f"Command timed out after {timeout}s", success=False)
        except Exception as e:
            return ToolResult(output=f"Error: {e}", success=False)

    def _nmap(self, args: str) -> ToolResult:
        return self._run_cmd(f"nmap {args}", timeout=180)

    def _shell(self, args: str) -> ToolResult:
        return self._run_cmd(args, timeout=60)

    def _curl(self, args: str) -> ToolResult:
        return self._run_cmd(f"curl -s -H 'bypass-tunnel-reminder: true' -m 30 {args}")

    def _gobuster(self, args: str) -> ToolResult:
        return self._run_cmd(f"gobuster {args}", timeout=180)

    def _nikto(self, args: str) -> ToolResult:
        return self._run_cmd(f"nikto {args}", timeout=180)

    def _whatweb(self, args: str) -> ToolResult:
        return self._run_cmd(f"whatweb {args}", timeout=30)

    def _sqlmap(self, args: str) -> ToolResult:
        return self._run_cmd(f"sqlmap {args}", timeout=180)

    def _hydra(self, args: str) -> ToolResult:
        return self._run_cmd(f"hydra {args}", timeout=180)

    def _searchsploit(self, args: str) -> ToolResult:
        return self._run_cmd(f"searchsploit {args}")

    def _wget(self, args: str) -> ToolResult:
        return self._run_cmd(f"wget {args}", timeout=60)

    def _netcat(self, args: str) -> ToolResult:
        return self._run_cmd(f"nc {args}", timeout=30)

    def _python(self, args: str) -> ToolResult:
        return self._run_cmd(f"python3 {args}", timeout=60)

    def _grep(self, args: str) -> ToolResult:
        return self._run_cmd(f"grep {args}")

    def _file(self, args: str) -> ToolResult:
        return self._run_cmd(f"file {args}")

    def _strings(self, args: str) -> ToolResult:
        return self._run_cmd(f"strings {args}")

    def _exiftool(self, args: str) -> ToolResult:
        return self._run_cmd(f"exiftool {args}", timeout=60)

    def _binwalk(self, args: str) -> ToolResult:
        return self._run_cmd(f"binwalk {args}", timeout=60)

    def _ssh(self, args: str) -> ToolResult:
        # SSH is tricky in autonomous mode - typically need creds
        return self._run_cmd(f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {args}", timeout=30)

    def _submit_flag(self, flag: str) -> ToolResult:
        """Submit a flag (stores it for reporting)."""
        flag = flag.strip()
        logger.info(f"🚩 FLAG SUBMITTED: {flag}")
        # In a real CTF, this would submit to the scoring server
        # For HALctf, we store and report
        return ToolResult(output=f"Flag captured and stored: {flag}", success=True)

    def _quick_scan(self, target: str) -> ToolResult:
        """Fast comprehensive scan combining multiple tools."""
        target = target.strip()
        output_parts = []

        # 1. Quick nmap
        logger.info(f"🔍 Quick scan: nmap on {target}")
        nmap_result = self._run_cmd(
            f"nmap -sV -sC --top-ports 1000 -T4 {target}", timeout=120
        )
        output_parts.append(f"=== NMAP ===\n{nmap_result.output}")

        # 2. If web ports found, fingerprint
        web_ports = []
        for port_match in re.finditer(r'(\d+)/tcp\s+open\s+http', nmap_result.output):
            web_ports.append(port_match.group(1))

        if web_ports:
            for port in web_ports:
                protocol = "https" if port in ["443", "8443"] else "http"
                url = f"{protocol}://{target}:{port}" if port not in ["80", "443"] else f"{protocol}://{target}"

                logger.info(f"🌐 Web fingerprinting: {url}")
                whatweb_result = self._run_cmd(f"whatweb {url}", timeout=30)
                output_parts.append(f"=== WHATWEB ({url}) ===\n{whatweb_result.output}")

        combined = "\n\n".join(output_parts)
        return ToolResult(output=combined[:10000], success=True)
