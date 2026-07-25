"""Stage 4: DomainMapper (ACL) (<= 70 LOC)"""
from typing import Dict, Any
from .dtos import Observation

ALLOWED_KEYS = {"host", "port", "protocol", "state", "service", "domain", "ip"}

class DomainMapper:
    def map_to_domain(self, raw_item: Dict[str, Any], entity_type: str = "PORT") -> Observation:
        attrs = {k: v for k, v in raw_item.items() if k in ALLOWED_KEYS}
        key = f"{attrs.get('host', 'target')}:{attrs.get('port', '0')}"
        return Observation(entity_key=key, entity_type=entity_type, attributes=attrs)
