"""DTOs oficiais conforme Manifesto Recon Adapter v1.0"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set

@dataclass
class TargetSpec:
    kind: str  # DOMAIN | IP | CIDR | HOSTNAME | URL
    value: str

@dataclass
class ToolProfile:
    tool_name: str
    tool_version_constraint: str = "*"
    parser_version: str = "1.0.0"

@dataclass
class ReconRequest:
    request_id: str
    target: TargetSpec
    tool_profile: ToolProfile
    hard_timeout: float = 300.0
    memory_limit_mb: int = 512

@dataclass
class Observation:
    entity_key: str
    entity_type: str
    attributes: Dict[str, Any]

@dataclass
class Envelope:
    event_id: str
    canonical_hash: str
    observed_at: float
    schema_version: str = "1.0.0"

@dataclass
class EventClassI:
    envelope: Envelope
    observations: List[Observation]
