"""Stage 6: CanonicalHasher (<= 70 LOC)"""
import hashlib
import json
from typing import List
from .dtos import Observation

class CanonicalHasher:
    def compute_tau(self, obs_list: List[Observation]) -> str:
        serialized_items = []
        for obs in obs_list:
            sorted_attrs = dict(sorted(obs.attributes.items()))
            serialized_items.append(f"{obs.entity_type}:{obs.entity_key}:{json.dumps(sorted_attrs, sort_keys=True)}")
        canonical_str = "|".join(serialized_items)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
