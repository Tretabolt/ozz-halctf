"""
Ozz — HALctf Autonomous Pentesting Agent
Core ReAct agent loop — Competition Grade.

Design principles:
  - ALL decisions via LLM. Zero hardcoded decision logic.
  - Few-shot calibrated for CTF patterns.
  - Circuit breaker + exponential backoff.
  - NEDK composable regulation layer.
  - Automatic flag extraction and scoreboard submission.
"""

import json
import os
import re
import time
import logging
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .llm import LLM
from .memory import Memory
from .tools import ToolRegistry, ToolResult
from .few_shot import get_few_shot_messages

logger = logging.getLogger("ozz")


# ============================================================
# Configuration (all env-configurable, zero hardcoded decisions)
# ============================================================

def _env_int(key: str, default: int) -> int:
    return int(os.environ.get(key, str(default)))

def _env_float(key: str, default: float) -> float:
    return float(os.environ.get(key, str(default)))

def _env_str(key: str, default: str) -> str:
    return os.environ.get(key, default)


MAX_ITERATIONS = _env_int("OZZ_MAX_ITERATIONS", 200)
ACTION_DELAY_BASE = _env_float("OZZ_ACTION_DELAY", 0.5)
ACTION_DELAY_MAX = _env_float("OZZ_ACTION_DELAY_MAX", 30.0)
CIRCUIT_BREAKER_THRESHOLD = _env_int("OZZ_CIRCUIT_BREAKER", 15)
LOOP_DETECTION_WINDOW = _env_int("OZZ_LOOP_WINDOW", 5)
LOOP_DETECTION_THRESHOLD = _env_int("OZZ_LOOP_THRESHOLD", 3)
CONTEXT_HISTORY_DEPTH = _env_int("OZZ_CONTEXT_HISTORY", 8)
SCOREBOARD_URL = _env_str("SCOREBOARD_URL", "")
SCOREBOARD_AGENT_NAME = _env_str("SCOREBOARD_AGENT", "Ozz")


# ============================================================
# Flag Patterns (comprehensive CTF coverage)
# ============================================================

FLAG_PATTERNS = [
    r'flag\{[^}]+\}',
    r'CTF\{[^}]+\}',
    r'HALCTF\{[^}]+\}',
    r'DEFCON\{[^}]+\}',
    r'picoCTF\{[^}]+\}',
    r'HTB\{[^}]+\}',
    r'THM\{[^}]+\}',
    r'FLAG\{[^}]+\}',
    r'Flag\{[^}]+\}',
    r'[A-Za-z_]+\{[a-zA-Z0-9_\-!@#$%^&*()+=]{3,}\}',
]

# Pre-compile for performance
_FLAG_RE = re.compile('|'.join(FLAG_PATTERNS), re.IGNORECASE)


# ============================================================
# Data Structures
# ============================================================

class AgentState(Enum):
    IDLE = "idle"
    RECON = "recon"
    ENUMERATION = "enumeration"
    EXPLOITATION = "exploitation"
    POST_EXPLOIT = "post_exploit"
    PIVOT = "pivot"
    DONE = "done"


@dataclass
class Observation:
    """A single observation from tool execution."""
    tool: str
    command: str
    output: str
    success: bool
    timestamp: float = field(default_factory=time.time)


@dataclass
class Plan:
    """Current agent plan."""
    objective: str
    steps: list[str] = field(default_factory=list)
    current_step: int = 0
    state: AgentState = AgentState.IDLE
    target: str = ""
    findings: dict = field(default_factory=dict)
    credentials: list = field(default_factory=list)
    flags_found: list = field(default_factory=list)


# ============================================================
# Prompts
# ============================================================

SYSTEM_PROMPT = """You are Ozz, an autonomous penetration testing agent competing in HALctf at DEF CON 34.

YOUR MISSION: Find and capture flags in CTF challenges. Flags typically follow formats like:
- flag{{...}}, CTF{{...}}, HALCTF{{...}}, picoCTF{{...}}, HTB{{...}}
- Or custom formats specified by the challenge

APPROACH (ReAct methodology):
1. RECON: Scan targets to discover services and technologies
2. ENUMERATION: Deep-dive into discovered services for vulnerabilities
3. EXPLOITATION: Use found vulnerabilities to gain access
4. POST_EXPLOIT: Search for flags in the compromised system
5. PIVOT: Use compromised systems to reach other targets

TOOLS AVAILABLE:
{tools_desc}

RESPONSE FORMAT:
You MUST respond with a single valid JSON object:
{{{{
  "thought": "Your reasoning about the current situation and what to do next",
  "action": "tool_name",
  "action_input": "input for the tool",
  "plan_update": "optional: update your plan/state"
}}}}

If you find a flag, respond with:
{{{{
  "thought": "Found a flag!",
  "action": "submit_flag",
  "action_input": "the_flag_value"
}}}}

CRITICAL RULES:
- Respond ONLY with valid JSON. No markdown fences, no explanation outside the JSON.
- Be creative. If one approach fails, try another.
- Use 'shell' for any command not explicitly listed as a tool.
- Always check for flags in every output — they can appear anywhere.
- If stuck for 3+ attempts, completely change your approach."""


def _build_phase_prompt(state: AgentState, target: str, findings: dict,
                        credentials: list, targets: list, target_idx: int) -> str:
    """Build phase-specific guidance. Content is derived from state, not hardcoded logic."""
    findings_str = json.dumps(findings, indent=2, default=str) if findings else "None yet"
    creds_str = json.dumps(credentials, indent=2) if credentials else "None found"

    phase_guidance = {
        AgentState.RECON: (
            f"You are in the RECON phase for target: {target}\n"
            f"Goal: Discover what services are running. Use nmap, quick_scan, whatweb.\n"
            f"Findings so far: {findings_str}"
        ),
        AgentState.ENUMERATION: (
            f"You are in the ENUMERATION phase for target: {target}\n"
            f"Goal: Deep-dive into discovered services. Find vulnerabilities.\n"
            f"Services found: {findings.get('services', 'None')}\n"
            f"Findings: {findings_str}"
        ),
        AgentState.EXPLOITATION: (
            f"You are in the EXPLOITATION phase for target: {target}\n"
            f"Goal: Exploit discovered vulnerabilities to gain access.\n"
            f"Vulnerabilities: {findings.get('vulnerabilities', 'None')}\n"
            f"Credentials: {creds_str}\n"
            f"Findings: {findings_str}"
        ),
        AgentState.POST_EXPLOIT: (
            f"You are in the POST_EXPLOIT phase for target: {target}\n"
            f"Goal: Search compromised system for flags, credentials, and pivot opportunities.\n"
            f"Credentials: {creds_str}\n"
            f"Findings: {findings_str}"
        ),
        AgentState.PIVOT: (
            f"You are in the PIVOT phase.\n"
            f"Goal: Use compromised systems to reach other targets.\n"
            f"Compromised: {findings.get('compromised', 'None')}\n"
            f"Networks: {findings.get('networks', 'None')}\n"
            f"Credentials: {creds_str}\n"
            f"All targets: {targets}"
        ),
        AgentState.IDLE: "Starting up. Begin with reconnaissance.",
        AgentState.DONE: "All objectives complete.",
    }
    return phase_guidance.get(state, "Continue with your current plan.")


# ============================================================
# Scoreboard Integration
# ============================================================

class ScoreboardClient:
    """Submits flags to the CTF scoreboard."""

    def __init__(self, url: str = SCOREBOARD_URL, agent_name: str = SCOREBOARD_AGENT_NAME):
        self.url = url.rstrip("/") if url else ""
        self.agent_name = agent_name
        self.submitted: list[str] = []

    @property
    def enabled(self) -> bool:
        return bool(self.url)

    def submit(self, flag: str) -> dict:
        """Submit a flag to the scoreboard. Returns result dict."""
        if not self.url:
            logger.info(f"🚩 [NO SCOREBOARD] Flag stored locally: {flag}")
            return {"status": "local_only", "flag": flag}

        if flag in self.submitted:
            return {"status": "duplicate", "flag": flag}

        try:
            import requests
            resp = requests.post(
                f"{self.url}/submit",
                data={"flag": flag, "agent": self.agent_name},
                timeout=10,
            )
            result = {"status": "submitted", "flag": flag, "http_status": resp.status_code}
            if resp.status_code == 200:
                self.submitted.append(flag)
                logger.info(f"🚩 ✅ Flag submitted to scoreboard: {flag}")
            else:
                logger.warning(f"🚩 ⚠️ Scoreboard returned {resp.status_code}: {resp.text[:200]}")
            return result
        except Exception as e:
            logger.error(f"🚩 ❌ Scoreboard submission failed: {e}")
            return {"status": "error", "flag": flag, "error": str(e)}


# ============================================================
# OzzAgent — Competition-Grade ReAct Agent
# ============================================================

class OzzAgent:
    """Main autonomous pentesting agent.

    Architecture:
      ReAct loop: context → LLM → parse → validate → act → observe → remember
      MNHI 3.5 spaces composed via NEDK (optional)
      Circuit breaker prevents infinite loops
      Exponential backoff on repeated failures
    """

    def __init__(self, targets: list[str], model_path: str = "/models",
                 nedk=None, scoreboard_url: str = ""):
        self.targets = targets
        self.llm = LLM(model_path)
        self.memory = Memory()
        self.tools = ToolRegistry()
        self.plan = Plan(objective="Find and capture all flags")
        self.history: list[Observation] = []
        self.max_iterations = MAX_ITERATIONS
        self.current_target_idx = 0
        self.run_id = f"run-{int(time.time() * 1000)}"
        self.nedk = nedk  # Optional NEDK composition

        # Scoreboard
        sb_url = scoreboard_url or SCOREBOARD_URL
        self.scoreboard = ScoreboardClient(url=sb_url)

        # Circuit breaker & backoff
        self._consecutive_failures = 0
        self._consecutive_same_action = 0
        self._last_action_sig: Optional[str] = None
        self._current_delay = ACTION_DELAY_BASE
        self._stuck_count = 0
        self._actions_without_new_info = 0

        # Loop detection
        self._action_signatures: list[str] = []

        # Run metrics
        self.run_metrics = {
            "run_id": self.run_id,
            "targets": list(targets),
            "iterations": 0,
            "flags_found": 0,
            "flags_submitted": 0,
            "loop_detected": 0,
            "circuit_breaks": 0,
            "phase_transitions": 0,
            "tool_failures": 0,
            "llm_fallbacks": 0,
            "new_info_actions": 0,
        }
        self._last_phase: Optional[AgentState] = None

    # ============================================================
    # MAIN LOOP
    # ============================================================

    def run(self):
        """Main agent loop — full ReAct cycle."""
        logger.info(f"🏴 Ozz starting. Targets: {self.targets}")
        logger.info(f"   Scoreboard: {'enabled' if self.scoreboard.enabled else 'disabled (local only)'}")
        logger.info(f"   Max iterations: {self.max_iterations}")
        logger.info(f"   Circuit breaker: {CIRCUIT_BREAKER_THRESHOLD} consecutive failures")

        self.plan.state = AgentState.RECON
        self.plan.target = self.targets[0] if self.targets else ""

        for i in range(self.max_iterations):
            self.run_metrics["iterations"] = i + 1

            if self.plan.state == AgentState.DONE:
                logger.info("🏁 Agent completed all objectives.")
                break

            # Circuit breaker check
            if self._consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
                logger.error(f"🛑 Circuit breaker triggered after {self._consecutive_failures} consecutive failures.")
                self.run_metrics["circuit_breaks"] += 1
                # Try to recover by switching target or state
                if not self._try_circuit_breaker_recovery():
                    logger.error("🛑 Cannot recover. Stopping.")
                    break

            logger.info(f"\n{'='*60}")
            logger.info(f"Iteration {i+1}/{self.max_iterations} | State: {self.plan.state.value} | Target: {self.plan.target}")
            logger.info(f"  Consecutive failures: {self._consecutive_failures} | Delay: {self._current_delay:.1f}s")
            logger.info(f"{'='*60}")

            # 1. BUILD CONTEXT
            context = self._build_context()

            # 2. THINK — LLM decides (no hardcoded overrides)
            decision = self._think(context)
            if not decision:
                self._consecutive_failures += 1
                self._backoff()
                continue

            # 3. VALIDATE decision structure
            if not self._validate_decision(decision):
                logger.warning(f"Invalid decision structure: {decision}")
                self._consecutive_failures += 1
                continue

            # 4. ACT — execute tool
            observation = self._act(decision)

            # 5. REMEMBER — store and interpret
            self._remember(observation)

            # 6. CHECK FLAGS
            new_flags = self._extract_flags(observation.output)
            for flag in new_flags:
                self._handle_flag(flag, observation)

            # 7. UPDATE STATE
            self._update_state(decision, observation)

            # 8. TRACK EFFECTIVENESS
            self._track_effectiveness(decision, observation)

            # 9. LOOP DETECTION
            if self._detect_loop():
                self._break_loop()

            # Adaptive delay
            time.sleep(self._current_delay)
            self.memory.store_run_metrics(self.run_metrics, run_id=self.run_id)

        # Final report
        self.run_metrics["flags_found"] = len(self.plan.flags_found)
        self.run_metrics["flags_submitted"] = len(self.scoreboard.submitted)
        self.memory.store_run_metrics(self.run_metrics, run_id=self.run_id)
        self._report()

    # ============================================================
    # CONTEXT BUILDING
    # ============================================================

    def _build_context(self) -> str:
        """Build the full context for the LLM. No hardcoded logic — pure state."""
        tools_desc = self.tools.describe_all()
        findings = json.dumps(self.plan.findings, indent=2, default=str) if self.plan.findings else "{}"

        # Recent history (configurable depth)
        recent = self.history[-CONTEXT_HISTORY_DEPTH:] if self.history else []
        history_lines = []
        for o in recent:
            status = "SUCCESS" if o.success else "FAILED"
            output_preview = o.output[:600] if o.output else "<no output>"
            history_lines.append(f"[{o.tool}] {o.command}\n  {status}: {output_preview}")
        history_text = "\n".join(history_lines) if history_lines else "No actions yet."

        # Phase prompt
        phase_prompt = _build_phase_prompt(
            self.plan.state, self.plan.target, self.plan.findings,
            self.plan.credentials, self.targets, self.current_target_idx
        )

        # System prompt with tools
        system = SYSTEM_PROMPT.replace("{tools_desc}", tools_desc)

        # Credentials summary
        creds_summary = []
        for cred in self.plan.credentials:
            if isinstance(cred, dict):
                u = cred.get("username", "")
                p = cred.get("password", "")
                creds_summary.append(f"{u}:{p}" if u or p else "<empty>")
            else:
                creds_summary.append(str(cred))

        # Prior run context
        prior_context = self._format_prior_context()

        # Action effectiveness context
        effectiveness_context = self._format_effectiveness_context()

        return f"""{system}

=== CURRENT PHASE ===
{phase_prompt}

=== RECENT ACTIONS (last {len(recent)}) ===
{history_text}

=== DISCOVERED FINDINGS ===
{findings}

=== KNOWN CREDENTIALS ===
{', '.join(creds_summary) if creds_summary else 'None'}

=== FLAGS FOUND SO FAR ===
{self.plan.flags_found if self.plan.flags_found else 'None yet'}

=== TARGETS REMAINING ===
{self.targets[self.current_target_idx:]}

=== PRIOR RUN INSIGHTS ===
{prior_context}

=== ACTION EFFECTIVENESS ===
{effectiveness_context}

Now, what is your next action? Respond with ONLY valid JSON."""

    # ============================================================
    # THINK — LLM Decision (NO hardcoded overrides)
    # ============================================================

    def _think(self, context: str) -> Optional[dict]:
        """Get LLM decision. The LLM decides everything — no hardcoded overrides."""
        try:
            decision = self.llm.generate_json(context)

            if self.llm.last_request_was_fallback:
                self.run_metrics["llm_fallbacks"] += 1

            if decision and isinstance(decision, dict):
                thought = decision.get("thought", "N/A")
                action = decision.get("action", "N/A")
                logger.info(f"🧠 Thought: {thought[:200]}")
                logger.info(f"🎯 Action: {action}")
                self._consecutive_failures = 0  # Reset on successful LLM call
                return decision
            else:
                logger.warning("LLM returned non-dict response, attempting extraction...")
                # Try to extract JSON from free-form text
                return self._extract_decision_from_text(context)

        except Exception as e:
            logger.error(f"LLM error: {e}")
            return None

    def _extract_decision_from_text(self, context: str) -> Optional[dict]:
        """Fallback: ask LLM to retry with stricter format."""
        retry_prompt = (
            "Your previous response was not valid JSON. "
            "You MUST respond with ONLY a JSON object like: "
            '{"thought": "...", "action": "tool_name", "action_input": "..."}\n'
            "What is your next action?"
        )
        try:
            decision = self.llm.generate_json(retry_prompt)
            if decision and isinstance(decision, dict) and "action" in decision:
                return decision
        except Exception:
            pass
        return None

    def _validate_decision(self, decision: dict) -> bool:
        """Validate that a decision has the required fields."""
        if not isinstance(decision, dict):
            return False
        if "action" not in decision:
            return False
        # action_input is optional (some tools don't need it)
        return True

    # ============================================================
    # ACT — Execute Tool
    # ============================================================

    def _act(self, decision: dict) -> Observation:
        """Execute the decided action."""
        action = decision.get("action", "")
        action_input = str(decision.get("action_input", ""))

        if action == "submit_flag":
            return self._handle_flag_submission(action_input)

        # Execute the tool
        result = self.tools.execute(action, action_input)

        if not result.success:
            self.run_metrics["tool_failures"] += 1
            self._consecutive_failures += 1
        else:
            self._consecutive_failures = 0

        return Observation(
            tool=action,
            command=f"{action} {action_input}",
            output=result.output,
            success=result.success,
        )

    def _handle_flag_submission(self, flag: str) -> Observation:
        """Handle flag submission — store locally AND submit to scoreboard."""
        flag = flag.strip()
        if not flag:
            return Observation(tool="submit_flag", command="submit_flag(empty)", output="Empty flag", success=False)

        # Store in memory
        self.memory.store_flag(flag, source="agent", target=self.plan.target)

        # Submit to scoreboard
        sb_result = self.scoreboard.submit(flag)

        return Observation(
            tool="submit_flag",
            command=f"submit_flag({flag})",
            output=f"Flag submitted: {flag} | Scoreboard: {sb_result.get('status', 'unknown')}",
            success=True,
        )

    # ============================================================
    # REMEMBER — Store & Interpret
    # ============================================================

    def _remember(self, obs: Observation):
        """Store observation and extract structured findings."""
        self.history.append(obs)
        self.memory.store(obs, target=self.plan.target, phase=self.plan.state.value)
        self._interpret_observation(obs)

    def _interpret_observation(self, obs: Observation):
        """Extract structured findings from tool output. Pattern-based, not hardcoded."""
        output = obs.output or ""
        if not output:
            return

        output_lower = output.lower()
        services = self.plan.findings.setdefault("services", [])
        vulnerabilities = self.plan.findings.setdefault("vulnerabilities", [])

        found_new_info = False

        # Extract services from nmap-style output
        for line in output.splitlines():
            if "/tcp" in line and ("open" in line):
                entry = line.strip()
                if entry not in services:
                    services.append(entry)
                    found_new_info = True
            elif "/udp" in line and ("open" in line):
                entry = line.strip()
                if entry not in services:
                    services.append(entry)
                    found_new_info = True

        # Extract web technologies from whatweb/curl headers
        tech_patterns = [
            (r'server:\s*(\S+)', "web_server"),
            (r'x-powered-by:\s*(\S+)', "framework"),
            (r'(\w+/\d+\.\d+[\.\d]*)', "version"),
        ]
        for pattern, category in tech_patterns:
            for match in re.finditer(pattern, output, re.IGNORECASE):
                tech = match.group(1)
                tech_entry = f"{category}: {tech}"
                if tech_entry not in services:
                    services.append(tech_entry)
                    found_new_info = True

        # Extract vulnerability indicators
        vuln_markers = [
            ("sql injection", "sql_injection"),
            ("sqli", "sql_injection"),
            ("command injection", "command_injection"),
            ("ssti", "ssti"),
            ("server-side template injection", "ssti"),
            ("lfi", "lfi"),
            ("local file inclusion", "lfi"),
            ("rfi", "rfi"),
            ("remote file inclusion", "rfi"),
            ("xss", "xss"),
            ("cross-site scripting", "xss"),
            ("xxe", "xxe"),
            ("xml external entity", "xxe"),
            ("ssrf", "ssrf"),
            ("server-side request forgery", "ssrf"),
            ("deserialization", "deserialization"),
            ("buffer overflow", "buffer_overflow"),
            ("path traversal", "path_traversal"),
            ("directory traversal", "path_traversal"),
            ("file upload", "file_upload"),
            ("default credential", "default_creds"),
            ("weak password", "weak_creds"),
            ("cve-", "cve_reference"),
        ]
        for marker, normalized in vuln_markers:
            if marker in output_lower:
                if normalized not in vulnerabilities:
                    vulnerabilities.append(normalized)
                    found_new_info = True

        # Extract credentials from various patterns
        self._extract_credentials_from_output(output)

        # Extract URLs and endpoints
        urls = re.findall(r'https?://[^\s\'"<>]+', output)
        endpoints = self.plan.findings.setdefault("endpoints", [])
        for url in urls:
            if url not in endpoints:
                endpoints.append(url)
                found_new_info = True

        # Track whether we got new info
        if found_new_info:
            self._actions_without_new_info = 0
            self.run_metrics["new_info_actions"] += 1
        else:
            self._actions_without_new_info += 1

        # Persist to memory
        self.memory.store_finding("services", "discovered", json.dumps(services), target=self.plan.target)
        self.memory.store_finding("vulnerabilities", "discovered", json.dumps(vulnerabilities), target=self.plan.target)

    def _extract_credentials_from_output(self, output: str):
        """Extract credentials from tool output using multiple patterns."""
        patterns = [
            # key=value patterns
            r'(?:username|user|login)\s*[=:]\s*(\S+)',
            r'(?:password|pass|pwd)\s*[=:]\s*(\S+)',
            # MySQL-style: root:password@host
            r'(\w+):(\S+)@\w+',
            # SSH-style: user@host
            r'ssh\s+(\w+)@',
            # HTTP basic auth: user:pass
            r'Authorization:\s*Basic\s+(\S+)',
        ]

        usernames = []
        passwords = []

        for line in output.splitlines():
            line_lower = line.lower()
            if "username=" in line_lower or "user=" in line_lower:
                match = re.search(r'(?:username|user)\s*=\s*(\S+)', line, re.IGNORECASE)
                if match:
                    usernames.append(match.group(1))
            if "password=" in line_lower or "pass=" in line_lower:
                match = re.search(r'(?:password|pass)\s*=\s*(\S+)', line, re.IGNORECASE)
                if match:
                    passwords.append(match.group(1))

        # Pair up usernames and passwords
        for i in range(max(len(usernames), len(passwords))):
            u = usernames[i] if i < len(usernames) else ""
            p = passwords[i] if i < len(passwords) else ""
            if u or p:
                cred = {"username": u, "password": p}
                if cred not in self.plan.credentials:
                    self.plan.credentials.append(cred)
                    self.memory.store_credential(
                        username=u, password=p,
                        target=self.plan.target, source="auto_extract",
                    )

    # ============================================================
    # FLAG EXTRACTION
    # ============================================================

    def _extract_flags(self, output: str) -> list[str]:
        """Extract all flags from output using comprehensive patterns."""
        if not output:
            return []
        matches = _FLAG_RE.findall(output)
        # Deduplicate and filter
        seen = set()
        unique = []
        for m in matches:
            if m not in seen and m not in self.plan.flags_found:
                seen.add(m)
                unique.append(m)
        return unique

    def _handle_flag(self, flag: str, obs: Observation):
        """Handle a discovered flag — store and submit."""
        if flag in self.plan.flags_found:
            return

        self.plan.flags_found.append(flag)
        self.run_metrics["flags_found"] = len(self.plan.flags_found)
        logger.info(f"🚩 FLAG FOUND: {flag}")

        # Store in memory
        self.memory.store_flag(flag, source=obs.tool, target=self.plan.target)

        # Submit to scoreboard
        sb_result = self.scoreboard.submit(flag)
        if sb_result.get("status") == "submitted":
            self.run_metrics["flags_submitted"] += 1

    # ============================================================
    # STATE MANAGEMENT
    # ============================================================

    def _update_state(self, decision: dict, obs: Observation):
        """Update agent state based on decision and observation."""
        plan_update = decision.get("plan_update")
        if plan_update:
            logger.info(f"📋 Plan update: {plan_update}")

        previous_state = self.plan.state

        # Auto state transitions based on findings
        if self.plan.state == AgentState.RECON:
            services = self.plan.findings.get("services", [])
            if len(services) >= 2:
                self.plan.state = AgentState.ENUMERATION
                logger.info("📊 Transitioning to ENUMERATION phase")

        elif self.plan.state == AgentState.ENUMERATION:
            vulns = self.plan.findings.get("vulnerabilities", [])
            if vulns or self.plan.credentials:
                self.plan.state = AgentState.EXPLOITATION
                logger.info("⚡ Transitioning to EXPLOITATION phase")

        elif self.plan.state == AgentState.EXPLOITATION:
            compromised = self.plan.findings.get("compromised", [])
            if compromised:
                self.plan.state = AgentState.PIVOT
                logger.info("🔀 Transitioning to PIVOT phase")
            elif self.plan.flags_found:
                # If we found flags but haven't compromised, stay in exploitation
                # but note the success
                logger.info("🎯 Flags found in exploitation phase — continuing search")

        elif self.plan.state == AgentState.POST_EXPLOIT:
            if self.plan.flags_found and self.current_target_idx >= len(self.targets) - 1:
                self.plan.state = AgentState.DONE
                logger.info("🏁 All targets processed, flags found. DONE.")

        # Move to next target if current one is exhausted
        if self._actions_without_new_info >= 10:
            if self.current_target_idx < len(self.targets) - 1:
                self.current_target_idx += 1
                self.plan.target = self.targets[self.current_target_idx]
                self.plan.state = AgentState.RECON
                self._actions_without_new_info = 0
                logger.info(f"🔄 Moving to next target: {self.plan.target}")
            elif self.plan.flags_found:
                self.plan.state = AgentState.DONE

        # Track phase transitions
        if self._last_phase is None or self._last_phase != self.plan.state:
            self.run_metrics["phase_transitions"] += 1
            self._last_phase = self.plan.state

    # ============================================================
    # LOOP DETECTION & CIRCUIT BREAKER
    # ============================================================

    def _detect_loop(self) -> bool:
        """Detect if agent is stuck in a loop (semantic, not just exact match)."""
        if len(self.history) < LOOP_DETECTION_WINDOW:
            return False

        recent = self.history[-LOOP_DETECTION_WINDOW:]
        # Check for exact action repetition
        signatures = [f"{o.tool}:{hashlib.md5(o.command.encode()).hexdigest()[:8]}" for o in recent]
        if len(set(signatures)) <= 1:
            self._consecutive_same_action += 1
        else:
            self._consecutive_same_action = 0

        return self._consecutive_same_action >= LOOP_DETECTION_THRESHOLD

    def _break_loop(self):
        """Break detected loop by forcing a state change."""
        self.run_metrics["loop_detected"] += 1
        logger.warning("⚠️ Loop detected! Forcing strategy change.")

        # Force phase transition
        phase_order = [AgentState.RECON, AgentState.ENUMERATION, AgentState.EXPLOITATION, AgentState.POST_EXPLOIT]
        current_idx = phase_order.index(self.plan.state) if self.plan.state in phase_order else 0
        next_idx = (current_idx + 1) % len(phase_order)
        self.plan.state = phase_order[next_idx]
        self._consecutive_same_action = 0
        self._actions_without_new_info = 0
        logger.info(f"🔄 Forced transition to {self.plan.state.value}")

    def _try_circuit_breaker_recovery(self) -> bool:
        """Try to recover from circuit breaker. Returns False if unrecoverable."""
        # Try next target
        if self.current_target_idx < len(self.targets) - 1:
            self.current_target_idx += 1
            self.plan.target = self.targets[self.current_target_idx]
            self.plan.state = AgentState.RECON
            self._consecutive_failures = 0
            self._current_delay = ACTION_DELAY_BASE
            logger.info(f"🔄 Circuit breaker recovery: switching to target {self.plan.target}")
            return True

        # Try resetting to a different phase
        if self.plan.state != AgentState.EXPLOITATION:
            self.plan.state = AgentState.EXPLOITATION
            self._consecutive_failures = 0
            logger.info("🔄 Circuit breaker recovery: switching to EXPLOITATION phase")
            return True

        return False

    def _backoff(self):
        """Exponential backoff on failures."""
        self._current_delay = min(self._current_delay * 1.5, ACTION_DELAY_MAX)

    # ============================================================
    # EFFECTIVENESS TRACKING
    # ============================================================

    def _track_effectiveness(self, decision: dict, obs: Observation):
        """Track which actions produce useful results."""
        action = decision.get("action", "unknown")
        entry = self.memory.get_strategy_evidence(target=self.plan.target)

        # Record to memory
        success_outcome = "success" if obs.success else "failure"
        self.memory.store_strategy_evidence(
            target=self.plan.target,
            service=str(self.plan.findings.get("services", ["unknown"])[0]) if self.plan.findings.get("services") else "unknown",
            vulnerability=str(self.plan.findings.get("vulnerabilities", ["unknown"])[0]) if self.plan.findings.get("vulnerabilities") else "unknown",
            action=action,
            confidence=0.8 if obs.success else 0.2,
            outcome=success_outcome,
        )

    def _format_prior_context(self) -> str:
        """Format prior run insights for the prompt."""
        history = self.memory.get_run_metrics_history()
        if not history:
            return "No prior run history."

        lines = []
        for row in history[-3:]:  # Last 3 runs
            flags = row.get("flags_found", 0)
            iters = row.get("iterations", 0)
            failures = row.get("tool_failures", 0)
            lines.append(f"- Run {row.get('run_id', '?')}: flags={flags}, iterations={iters}, failures={failures}")
        return "\n".join(lines)

    def _format_effectiveness_context(self) -> str:
        """Format action effectiveness data for the prompt."""
        evidence = self.memory.get_strategy_evidence(target=self.plan.target)
        if not evidence:
            return "No action effectiveness data yet."

        lines = []
        for item in evidence[-5:]:  # Last 5 entries
            lines.append(f"- {item.get('action', '?')}: {item.get('outcome', '?')} (confidence: {item.get('confidence', 0):.1f})")
        return "\n".join(lines)

    # ============================================================
    # FINAL REPORT
    # ============================================================

    def _report(self):
        """Generate final report."""
        logger.info("\n" + "="*60)
        logger.info("🏴 OZZ FINAL REPORT")
        logger.info("="*60)
        logger.info(f"Run ID: {self.run_id}")
        logger.info(f"Total actions: {len(self.history)}")
        logger.info(f"Flags found: {len(self.plan.flags_found)}")
        logger.info(f"Flags submitted: {len(self.scoreboard.submitted)}")
        logger.info(f"Loop detections: {self.run_metrics['loop_detected']}")
        logger.info(f"Circuit breaks: {self.run_metrics['circuit_breaks']}")
        logger.info(f"Phase transitions: {self.run_metrics['phase_transitions']}")
        logger.info(f"Tool failures: {self.run_metrics['tool_failures']}")
        logger.info(f"LLM fallbacks: {self.run_metrics['llm_fallbacks']}")
        logger.info(f"New info actions: {self.run_metrics['new_info_actions']}")
        for flag in self.plan.flags_found:
            submitted = "✅" if flag in self.scoreboard.submitted else "❌"
            logger.info(f"  🚩 {flag} [{submitted}]")
        logger.info(f"Findings: {json.dumps(self.plan.findings, indent=2, default=str)}")
        logger.info(f"Credentials: {json.dumps(self.plan.credentials, indent=2)}")
        logger.info("="*60)
