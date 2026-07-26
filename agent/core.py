"""
Ozz — HALctf Autonomous Pentesting Agent
Core ReAct agent loop.
"""

import json
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .llm import LLM
from .memory import Memory
from .tools import ToolRegistry, ToolResult

logger = logging.getLogger("ozz")


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


SYSTEM_PROMPT = """You are Ozz, an autonomous penetration testing agent competing in HALctf at DEF CON 34.

YOUR MISSION: Find and capture flags in CTF challenges. Flags typically follow formats like:
- flag{...}
- CTF{...}
- HALCTF{...}
- Or custom formats specified by the challenge

APPROACH:
1. RECON: Scan targets to discover services and technologies
2. ENUMERATION: Deep-dive into discovered services for vulnerabilities
3. EXPLOITATION: Use found vulnerabilities to gain access
4. POST-EXPLOIT: Search for flags in the compromised system
5. PIVOT: Use compromised systems to reach other targets

TOOLS AVAILABLE:
{tools_desc}

RESPONSE FORMAT:
You must respond with a JSON object:
{{
  "thought": "Your reasoning about the current situation and what to do next",
  "action": "tool_name",
  "action_input": "input for the tool",
  "plan_update": "optional: update your plan/state"
}}

If you find a flag, respond with:
{{
  "thought": "Found a flag!",
  "action": "submit_flag",
  "action_input": "the_flag_value"
}}

If you're stuck, try a different approach. Be creative. Think like a hacker.
Respond ONLY with valid JSON. No markdown, no explanation outside the JSON."""

RECON_PROMPT = """You are in the RECON phase. Your goal is to discover what's running on the target.

Current target: {target}
Previous findings: {findings}

What's your next recon step? Consider:
- Port scanning (nmap)
- Service detection
- Web directory enumeration
- DNS/subdomain discovery
- Banner grabbing"""

ENUM_PROMPT = """You are in the ENUMERATION phase. You've found services and need to dig deeper.

Current target: {target}
Services found: {services}
Previous findings: {findings}

What's your next enumeration step? Consider:
- Web app scanning (nikto, whatweb)
- Directory bruteforcing (gobuster, dirb)
- Service-specific enumeration (SMB, NFS, SSH)
- Version detection and vulnerability lookup
- Credential testing"""

EXPLOIT_PROMPT = """You are in the EXPLOITATION phase. You've identified potential vulnerabilities.

Current target: {target}
Vulnerabilities found: {vulns}
Credentials found: {creds}
Previous findings: {findings}

What's your next exploit attempt? Consider:
- Known exploit scripts (searchsploit)
- Credential stuffing
- Command injection
- SQL injection
- File upload vulnerabilities
- Default credentials
- Reverse shells"""

PIVOT_PROMPT = """You are in the PIVOT phase. You've compromised a system and need to reach others.

Compromised hosts: {compromised}
Discovered networks: {networks}
Credentials found: {creds}
All targets: {targets}

What's your next pivot step? Consider:
- Internal network scanning from compromised host
- Credential reuse on other targets
- Tunneling/proxying
- SSH pivoting
- ARP scanning"""


class OzzAgent:
    """Main autonomous pentesting agent."""

    def __init__(self, targets: list[str], model_path: str = "/models"):
        self.targets = targets
        self.llm = LLM(model_path)
        self.memory = Memory()
        self.tools = ToolRegistry()
        self.plan = Plan(objective="Find and capture all flags")
        self.history: list[Observation] = []
        self.max_iterations = 200
        self.current_target_idx = 0
        self.run_id = f"run-{int(time.time() * 1000)}"
        self.run_metrics = {
            "run_id": self.run_id,
            "targets": list(targets),
            "iterations": 0,
            "flags_found": 0,
            "loop_detected": 0,
            "phase_transitions": 0,
            "tool_failures": 0,
            "llm_fallbacks": 0,
        }
        self._last_phase: Optional[AgentState] = None
        self._consecutive_action_repeats = 0
        self.action_effectiveness: dict[str, dict] = {}
        self.prior_run_insights: dict = {}

    def run(self):
        """Main agent loop."""
        logger.info(f"🏴 Ozz starting. Targets: {self.targets}")
        self.plan.state = AgentState.RECON
        self.plan.target = self.targets[0] if self.targets else ""

        for i in range(self.max_iterations):
            self.run_metrics["iterations"] = i + 1
            if self.plan.state == AgentState.DONE:
                logger.info("🏁 Agent completed all objectives.")
                break

            logger.info(f"\n{'='*60}")
            logger.info(f"Iteration {i+1} | State: {self.plan.state.value} | Target: {self.plan.target}")
            logger.info(f"{'='*60}")

            # 1. Observe — build context
            context = self._build_context()

            # 2. Think — get LLM decision
            decision = self._think(context)
            if not decision:
                logger.warning("LLM returned no decision, retrying...")
                continue

            # 3. Act — execute tool
            observation = self._act(decision)

            # 4. Remember — store result
            self._remember(observation)

            # 5. Check for flags in output
            self._check_flags(observation.output)

            # 6. Update state if needed
            self._update_state(decision, observation)

            # Small delay to not overwhelm targets
            time.sleep(0.5)
            self.memory.store_run_metrics(self.run_metrics, run_id=self.run_id)

        # Final report
        self.run_metrics["flags_found"] = len(self.plan.flags_found)
        self.memory.store_run_metrics(self.run_metrics, run_id=self.run_id)
        self._report()

    def _build_context(self) -> str:
        """Build the context for the LLM."""
        tools = getattr(self, "tools", None)
        tools_desc = tools.describe_all() if tools is not None else "No tools available"
        findings = json.dumps(self.plan.findings, indent=2, default=str)

        # Get recent history (last 5 observations)
        recent = self.history[-5:] if self.history else []
        history_text = "\n".join(
            f"[{o.tool}] {o.command}\n{'SUCCESS' if o.success else 'FAILED'}: {o.output[:500]}"
            for o in recent
        )

        # Build phase-specific prompt
        if self.plan.state == AgentState.RECON:
            phase_prompt = RECON_PROMPT.format(
                target=self.plan.target,
                findings=findings
            )
        elif self.plan.state == AgentState.ENUMERATION:
            services = self.plan.findings.get("services", "None discovered yet")
            phase_prompt = ENUM_PROMPT.format(
                target=self.plan.target,
                services=services,
                findings=findings
            )
        elif self.plan.state == AgentState.EXPLOITATION:
            vulns = self.plan.findings.get("vulnerabilities", [])
            creds = self.plan.credentials
            phase_prompt = EXPLOIT_PROMPT.format(
                target=self.plan.target,
                vulns=vulns,
                creds=creds,
                findings=findings
            )
        elif self.plan.state == AgentState.PIVOT:
            phase_prompt = PIVOT_PROMPT.format(
                compromised=self.plan.findings.get("compromised", []),
                networks=self.plan.findings.get("networks", []),
                creds=self.plan.credentials,
                targets=self.targets
            )
        else:
            phase_prompt = "Continue with your current plan."

        system = SYSTEM_PROMPT.replace("{tools_desc}", tools_desc)

        credentials_summary = []
        for cred in self.plan.credentials:
            if isinstance(cred, dict):
                username = cred.get("username", "")
                password = cred.get("password", "")
                credentials_summary.append(f"{username}:{password}" if username or password else "<empty>")
            else:
                credentials_summary.append(str(cred))

        prior_strategy_text = self._format_prior_strategy_context()
        exploit_reference_text = self._format_exploit_reference_context()
        service_strategy_text = self._format_service_strategy_context()

        return f"""{system}

=== CURRENT PHASE ===
{phase_prompt}

=== RECENT ACTIONS ===
{history_text}

=== DISCOVERED FINDINGS ===
{findings}

=== KNOWN CREDENTIALS ===
{credentials_summary if credentials_summary else 'None'}

=== PRIOR RUN STRATEGIES ===
{prior_strategy_text}

=== EXPLOIT REFERENCE CONTEXT ===
{exploit_reference_text}

=== SERVICE-SPECIFIC STRATEGY ===
{service_strategy_text}

=== FLAGS FOUND SO FAR ===
{self.plan.flags_found}

=== TARGETS REMAINING ===
{self.targets[self.current_target_idx:]}

Now, what's your next action?"""

    def _think(self, context: str) -> Optional[dict]:
        """Get LLM decision with Anti-Loop Psi-Stabilizer."""
        # 1. Verificar Anti-Loop (Hash das últimas 5 ações)
        if len(self.history) >= 3:
            recent_signatures = [f"{o.tool}:{o.command}" for o in self.history[-3:]]
            if len(set(recent_signatures)) == 1:
                self._consecutive_action_repeats += 1
                if self._consecutive_action_repeats >= 2:
                    self.run_metrics["loop_detected"] += 1
                    logger.warning("⚠️ Ψ-Stabilizer: Loop detectado! Forçando perturbação δS_aleatoria para mudar de foco.")
                    if self.plan.state == AgentState.RECON:
                        self.plan.state = AgentState.ENUMERATION
                    elif self.plan.state == AgentState.ENUMERATION:
                        self.plan.state = AgentState.EXPLOITATION
                    return {
                        "thought": "Psi-Stabilizer acionado para quebrar loop de execução repetida.",
                        "action": "quick_scan",
                        "action_input": self.plan.target
                    }
            else:
                self._consecutive_action_repeats = 0

        self.prior_run_insights = self._load_prior_run_insights()

        try:
            decision = self.llm.generate_json(context)
            if self.llm.last_request_was_fallback:
                self.run_metrics["llm_fallbacks"] += 1
                logger.warning("⚠️ LLM fallback endpoint was used for this request.")

            if decision and isinstance(decision, dict):
                logger.info(f"🧠 Thought: {decision.get('thought', 'N/A')}")
                logger.info(f"🎯 Action: {decision.get('action', 'N/A')}")
                if decision.get("action") in {"shell", "quick_scan", "curl", "ssh", "sqlmap", "nmap"}:
                    candidate_obs = Observation(tool=decision.get("action", ""), command=decision.get("action_input", ""), output=decision.get("action_input", ""), success=True)
                    if self.prior_run_insights.get("best_strategy"):
                        best_strategy = self.prior_run_insights["best_strategy"]
                        if best_strategy.get("flags_found", 0) > 0:
                            learning_guided = self._choose_learning_guided_action(candidate_obs)
                            if learning_guided.get("action"):
                                learning_guided["thought"] = decision.get("thought", "Strategy from prior successful runs")
                                learning_guided["plan_update"] = decision.get("plan_update")
                                return learning_guided
                    strategic_decision = self._select_next_action(candidate_obs)
                    learning_guided = self._choose_learning_guided_action(candidate_obs)
                    if learning_guided.get("action"):
                        learning_guided["thought"] = decision.get("thought", "Strategic selection")
                        learning_guided["plan_update"] = decision.get("plan_update")
                        return learning_guided
                    if strategic_decision.get("action"):
                        strategic_decision["thought"] = decision.get("thought", "Strategic selection")
                        strategic_decision["plan_update"] = decision.get("plan_update")
                        return strategic_decision
                return decision
            else:
                logger.warning("LLM respondeu sem estrutura JSON válida, usando fallback de extração.")
                return {"thought": "Resposta sem formato JSON claro", "action": "shell", "action_input": "echo 'parse error'"}
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return None

    def _act(self, decision: dict) -> Observation:
        """Execute the decided action."""
        action = decision.get("action", "")
        action_input = decision.get("action_input", "")

        if action == "submit_flag":
            # Special handling for flag submission
            return Observation(
                tool="submit_flag",
                command=f"submit_flag({action_input})",
                output=f"Flag submitted: {action_input}",
                success=True
            )

        # Execute the tool
        result = self.tools.execute(action, action_input)

        if not result.success:
            self.run_metrics["tool_failures"] += 1

        return Observation(
            tool=action,
            command=f"{action} {action_input}",
            output=result.output,
            success=result.success
        )

    def _remember(self, obs: Observation):
        """Store observation in memory."""
        self.history.append(obs)
        self.memory.store(obs)
        self._interpret_observation(obs)

    def _interpret_observation(self, obs: Observation):
        """Turn raw tool output into structured findings and credentials."""
        output = obs.output or ""
        if not output:
            return

        services = self.plan.findings.setdefault("services", [])
        vulnerabilities = self.plan.findings.setdefault("vulnerabilities", [])

        # Extract services from nmap-like output
        for line in output.splitlines():
            if "/tcp" in line and ("open" in line or "closed" in line):
                if line not in services:
                    services.append(line.strip())

        # Extract credentials from common patterns
        credential_pairs = []
        for line in output.splitlines():
            if "username=" in line.lower():
                key, value = line.split("=", 1)
                credential_pairs.append((key.strip().lower(), value.strip()))
            if "password=" in line.lower():
                key, value = line.split("=", 1)
                credential_pairs.append((key.strip().lower(), value.strip()))

        if credential_pairs:
            username = None
            password = None
            for key, value in credential_pairs:
                if key == "username":
                    username = value
                elif key == "password":
                    password = value
            if username or password:
                existing = any(
                    c.get("username") == username and c.get("password") == password
                    for c in self.plan.credentials
                )
                if not existing:
                    self.plan.credentials.append({"username": username or "", "password": password or ""})

        # Extract simple vulnerability hints
        vuln_markers = [
            ("sql injection", "sql injection"),
            ("command injection", "command injection"),
            ("ssti", "ssti"),
            ("lfi", "lfi"),
            ("sqli", "sql injection"),
            ("sqli", "sql injection"),
        ]
        for marker, normalized in vuln_markers:
            if marker.lower() in output.lower() and normalized not in vulnerabilities:
                vulnerabilities.append(normalized)

        self.memory.store_finding("services", "discovered", json.dumps(services), target=self.plan.target)
        self.memory.store_finding("vulnerabilities", "discovered", json.dumps(vulnerabilities), target=self.plan.target)

        if self.plan.credentials:
            latest = self.plan.credentials[-1]
            self.memory.store_credential(
                username=latest.get("username", ""),
                password=latest.get("password", ""),
                target=self.plan.target,
                source=obs.tool,
            )

    def _recommend_next_action(self, obs: Observation) -> dict:
        """Recommend a follow-up action based on observed service hints."""
        output = (obs.output or "").lower()
        if "80/tcp" in output or "http" in output:
            return {"action": "curl", "action_input": self.plan.target}
        if "22/tcp" in output or "ssh" in output:
            return {"action": "ssh", "action_input": f"-o BatchMode=yes {self.plan.target}"}
        if "3306" in output or "mysql" in output:
            return {"action": "sqlmap", "action_input": f"--batch {self.plan.target}"}
        return {"action": "quick_scan", "action_input": self.plan.target}

    def _select_next_action(self, obs: Observation) -> dict:
        """Select the most appropriate next action from current findings and service hints."""
        vulnerabilities = self.plan.findings.get("vulnerabilities", [])
        credentials = self.plan.credentials
        output = (obs.output or "").lower()

        if vulnerabilities:
            return {"action": "sqlmap", "action_input": f"--batch {self.plan.target}"}

        if credentials:
            return {"action": "ssh", "action_input": f"-o BatchMode=yes {self.plan.target}"}

        if "http" in output or "80/tcp" in output:
            return {"action": "curl", "action_input": self.plan.target}

        if "ssh" in output or "22/tcp" in output:
            return {"action": "ssh", "action_input": f"-o BatchMode=yes {self.plan.target}"}

        return self._recommend_next_action(obs)

    def _load_prior_run_insights(self) -> dict:
        """Load prior run metrics from memory to guide future behavior."""
        prior_runs = {}
        for row in self.memory.get_run_metrics_history():
            run_id = row.get("run_id")
            if not run_id:
                continue
            prior_runs[run_id] = row
        if not prior_runs:
            return {"best_runs": {}, "best_strategy": None}

        best_runs = sorted(prior_runs.items(), key=lambda item: (
            item[1].get("flags_found", 0),
            -item[1].get("tool_failures", 0),
            -item[1].get("iterations", 0),
        ), reverse=True)
        best_runs_dict = {run_id: metrics for run_id, metrics in best_runs[:3]}
        return {"best_runs": best_runs_dict, "best_strategy": best_runs[0][1] if best_runs else None}

    def _record_action_outcome(self, action: str, success: bool, output: str):
        """Track how useful an action was so the agent can avoid repeating failures."""
        entry = self.action_effectiveness.setdefault(action, {"successes": 0, "failures": 0, "last_output": ""})
        if success:
            entry["successes"] += 1
        else:
            entry["failures"] += 1
        entry["last_output"] = output[:200]

    def _format_prior_strategy_context(self) -> str:
        """Summarize successful prior strategies in a form useful for the LLM prompt."""
        self.prior_run_insights = self._load_prior_run_insights()
        if not self.prior_run_insights.get("best_runs"):
            return "No prior run history available."

        lines = []
        for run_id, metrics in self.prior_run_insights["best_runs"].items():
            flags = metrics.get("flags_found", 0)
            failures = metrics.get("tool_failures", 0)
            iterations = metrics.get("iterations", 0)
            lines.append(f"- {run_id}: flags={flags}, failures={failures}, iterations={iterations}")
        return "\n".join(lines)

    def _format_exploit_reference_context(self) -> str:
        """Add exploit-db and general exploit context when relevant services are present."""
        findings = self.plan.findings or {}
        services = findings.get("services", [])
        vulns = findings.get("vulnerabilities", [])
        if not services and not vulns:
            return "No exploit reference context needed yet."

        hints = []
        if any("http" in str(item).lower() for item in services):
            hints.append("Web services often expose SQLi/LFI/RFI/SSTI; consult Exploit-DB and vendor references for specific versions.")
        if any("ssh" in str(item).lower() for item in services):
            hints.append("SSH services may be vulnerable to credential reuse or known misconfigurations; consult Exploit-DB for service-specific issues.")
        if any("sql" in str(item).lower() for item in vulns):
            hints.append("SQL injection is a strong candidate for exploit research; review public exploit DB references and version-specific payloads.")

        return "\n".join([
            "Exploit-DB reference guidance:",
            "- Primary source: https://www.exploit-db.com",
            "- Use it to find public exploits or PoC references for the specific service/version discovered.",
            "- Cross-check the target version and match the PoC to the current environment before execution.",
            *hints,
        ])

    def _format_service_strategy_context(self) -> str:
        """Summarize service-specific strategy evidence from prior runs."""
        evidence = self.memory.get_strategy_evidence(target=self.plan.target)
        if not evidence:
            return "No service-specific strategy evidence available yet."

        lines = []
        for item in evidence:
            lines.append(
                f"- service={item.get('service') or 'unknown'} vulnerability={item.get('vulnerability') or 'unknown'} "
                f"action={item.get('action') or 'unknown'} reference={item.get('reference') or 'n/a'} "
                f"confidence={item.get('confidence', 0.0)} outcome={item.get('outcome', 'unknown')}"
            )
        return "\n".join(["Service-specific strategy evidence:", *lines])

    def _choose_learning_guided_action(self, obs: Observation) -> dict:
        """Choose a recovery action after repeated low-value outcomes."""
        action_name = (obs.tool or "").strip()
        if action_name:
            self._record_action_outcome(action_name, obs.success, obs.output)

        entry = self.action_effectiveness.get(action_name, {})
        failures = entry.get("failures", 0)
        if failures >= 2:
            return {"action": "quick_scan", "action_input": self.plan.target}

        return self._select_next_action(obs)

    def _build_hypotheses(self, obs: Observation) -> list[dict]:
        """Build a ranked set of hypotheses from the current state."""
        output = (obs.output or "").lower()
        hypotheses: list[dict] = []

        if "sql" in output or "sql injection" in output:
            hypotheses.append({
                "hypothesis": "A sql injection vulnerability is present and can be exploited against the target.",
                "priority": "high",
                "action": "sqlmap",
            })

        if self.plan.credentials:
            hypotheses.append({
                "hypothesis": "Known credentials may unlock an authenticated service or shell access.",
                "priority": "high",
                "action": "ssh",
            })

        if "http" in output or "80/tcp" in output:
            hypotheses.append({
                "hypothesis": "The service exposed on HTTP may reveal a web entry point for further exploitation.",
                "priority": "medium",
                "action": "curl",
            })

        if not hypotheses:
            hypotheses.append({
                "hypothesis": "The environment is still in reconnaissance and should be probed more broadly.",
                "priority": "low",
                "action": "quick_scan",
            })

        return sorted(hypotheses, key=lambda item: 0 if item["priority"] == "high" else 1)

    def _check_flags(self, output: str):
        """Check output for flags."""
        import re
        # Common flag patterns
        patterns = [
            r'flag\{[^}]+\}',
            r'CTF\{[^}]+\}',
            r'HALCTF\{[^}]+\}',
            r'DEFCON\{[^}]+\}',
            r'[A-Z]+\{[a-zA-Z0-9_!@#$%^&*()-]+\}',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            for match in matches:
                if match not in self.plan.flags_found:
                    self.plan.flags_found.append(match)
                    self.run_metrics["flags_found"] = len(self.plan.flags_found)
                    logger.info(f"🚩 FLAG FOUND: {match}")

    def _update_state(self, decision: dict, obs: Observation):
        """Update agent state based on decision and observation."""
        plan_update = decision.get("plan_update")
        if plan_update:
            logger.info(f"📋 Plan update: {plan_update}")

        previous_state = self.plan.state

        # Auto state transitions based on findings
        if self.plan.state == AgentState.RECON:
            # If we've done enough recon, move to enumeration
            recon_actions = sum(1 for o in self.history if o.tool in ["nmap", "masscan", "whatweb"])
            if recon_actions >= 3 and self.plan.findings.get("services"):
                self.plan.state = AgentState.ENUMERATION
                logger.info("📊 Transitioning to ENUMERATION phase")

        elif self.plan.state == AgentState.ENUMERATION:
            # If we've found potential vulns, move to exploitation
            if self.plan.findings.get("vulnerabilities") or self.plan.credentials:
                self.plan.state = AgentState.EXPLOITATION
                logger.info("⚡ Transitioning to EXPLOITATION phase")

        elif self.plan.state == AgentState.EXPLOITATION:
            # If we've compromised something, check for pivoting
            if self.plan.findings.get("compromised"):
                self.plan.state = AgentState.PIVOT
                logger.info("🔀 Transitioning to PIVOT phase")

        # Move to next target if current one is exhausted
        if self.plan.state in [AgentState.PIVOT, AgentState.DONE]:
            if self.current_target_idx < len(self.targets) - 1:
                self.current_target_idx += 1
                self.plan.target = self.targets[self.current_target_idx]
                self.plan.state = AgentState.RECON
                logger.info(f"🔄 Moving to next target: {self.plan.target}")

        if self._last_phase is None or self._last_phase != self.plan.state:
            self.run_metrics["phase_transitions"] += 1
            self._last_phase = self.plan.state

    def _report(self):
        """Generate final report."""
        logger.info("\n" + "="*60)
        logger.info("🏴 OZZ FINAL REPORT")
        logger.info("="*60)
        logger.info(f"Total actions: {len(self.history)}")
        logger.info(f"Flags found: {len(self.plan.flags_found)}")
        logger.info(f"Loop detections: {self.run_metrics['loop_detected']}")
        logger.info(f"Phase transitions: {self.run_metrics['phase_transitions']}")
        logger.info(f"Tool failures: {self.run_metrics['tool_failures']}")
        logger.info(f"LLM fallbacks used: {self.run_metrics.get('llm_fallbacks', 0)}")
        for flag in self.plan.flags_found:
            logger.info(f"  🚩 {flag}")
        logger.info(f"Findings: {json.dumps(self.plan.findings, indent=2, default=str)}")
        logger.info(f"Credentials: {self.plan.credentials}")
        logger.info(f"Run metrics: {json.dumps(self.run_metrics, indent=2, default=str)}")
        logger.info("="*60)
