"""Stage 5: Normalizer (<= 70 LOC)"""
from typing import List
from .dtos import Observation

class Normalizer:
    def normalize(self, obs_list: List[Observation]) -> List[Observation]:
        # Strip volatility (already done via ACL attributes filter) and sort lexicographically by entity_key
        return sorted(obs_list, key=lambda x: (x.entity_key, sorted(x.attributes.items())))
