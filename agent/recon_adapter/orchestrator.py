"""Orchestrator do Pipeline de 7 Estágios (<= 70 LOC)"""
import time
import uuid
from typing import Optional, Callable
from .dtos import ReconRequest, EventClassI, Envelope
from .validator import RequestValidator
from .parser import RawResultParser
from .mapper import DomainMapper
from .normalizer import Normalizer
from .hasher import CanonicalHasher
from .publisher import EventPublisher

class ReconAdapterOrchestrator:
    def __init__(self, event_mesh_publish_func: Optional[Callable] = None):
        self.validator = RequestValidator()
        self.parser = RawResultParser()
        self.mapper = DomainMapper()
        self.normalizer = Normalizer()
        self.hasher = CanonicalHasher()
        self.publisher = EventPublisher(event_mesh_publish_func)

    def process_raw(self, request: ReconRequest, raw_output: str) -> EventClassI:
        self.validator.validate(request)
        parsed = self.parser.parse(raw_output, request.tool_profile.tool_name)
        obs_list = [self.mapper.map_to_domain(item) for item in parsed]
        normalized = self.normalizer.normalize(obs_list)
        tau = self.hasher.compute_tau(normalized)
        envelope = Envelope(event_id=str(uuid.uuid4()), canonical_hash=tau, observed_at=time.time())
        event = EventClassI(envelope=envelope, observations=normalized)
        self.publisher.publish(event)
        return event
