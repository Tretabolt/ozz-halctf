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

    def run(self):
        """Main agent loop."""
        logger.info(f"🏴 Ozz starting. Targets: {self.targets}")
        self.plan.state = AgentState.RECON
        self.plan.target = self.targets[0] if self.targets else ""

        for i in range(self.max_iterations):
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

        # Final report
        self._report()

    def _build_context(self) -> str:
        """Build the context for the LLM."""
        tools_desc = self.tools.describe_all()
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

        system = SYSTEM_PROMPT.format(tools_desc=tools_desc)

        return f"""{system}

=== CURRENT PHASE ===
{phase_prompt}

=== RECENT ACTIONS ===
{history_text}

=== DISCOVERED FINDINGS ===
{findings}

=== FLAGS FOUND SO FAR ===
{self.plan.flags_found}

=== TARGETS REMAINING ===
{self.targets[self.current_target_idx:]}

Now, what's your next action?"""

    def _think(self, context: str) -> Optional[dict]:
        """Get LLM decision with Anti-Loop Psi-Stabilizer."""
        # 1. Verificar Anti-Loop (Hash das últimas 5 ações)
        if len(self.history) >= 5:
            last_5 = [f"{o.tool}:{o.command}" for o in self.history[-5:]]
            if len(set(last_5)) == 1:  # 5 ações idênticas seguidas
                logger.warning("⚠️ Ψ-Stabilizer: Loop detectado! Forçando perturbação δS_aleatoria para mudar de foco.")
                # Perturbação: Alternar fase ou resetar foco
                if self.plan.state == AgentState.RECON:
                    self.plan.state = AgentState.ENUMERATION
                elif self.plan.state == AgentState.ENUMERATION:
                    self.plan.state = AgentState.EXPLOITATION
                return {
                    "thought": "Psi-Stabilizer acionado para quebrar loop de execução repetida.",
                    "action": "nmap",
                    "action_input": f"-sV --top-ports 20 {self.plan.target}"
                }

        try:
            decision = self.llm.generate_json(context)
            if decision and isinstance(decision, dict):
                logger.info(f"🧠 Thought: {decision.get('thought', 'N/A')}")
                logger.info(f"🎯 Action: {decision.get('action', 'N/A')}")
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
                    logger.info(f"🚩 FLAG FOUND: {match}")

    def _update_state(self, decision: dict, obs: Observation):
        """Update agent state based on decision and observation."""
        plan_update = decision.get("plan_update")
        if plan_update:
            logger.info(f"📋 Plan update: {plan_update}")

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

    def _report(self):
        """Generate final report."""
        logger.info("\n" + "="*60)
        logger.info("🏴 OZZ FINAL REPORT")
        logger.info("="*60)
        logger.info(f"Total actions: {len(self.history)}")
        logger.info(f"Flags found: {len(self.plan.flags_found)}")
        for flag in self.plan.flags_found:
            logger.info(f"  🚩 {flag}")
        logger.info(f"Findings: {json.dumps(self.plan.findings, indent=2, default=str)}")
        logger.info(f"Credentials: {self.plan.credentials}")
        logger.info("="*60)
