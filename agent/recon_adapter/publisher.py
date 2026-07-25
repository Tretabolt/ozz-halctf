"""Stage 7: EventPublisher (<= 70 LOC)"""
from typing import Optional, Callable
from .dtos import EventClassI

class EventPublisher:
    def __init__(self, event_mesh_publish_func: Optional[Callable] = None):
        self.publish_func = event_mesh_publish_func

    def publish(self, event: EventClassI) -> bool:
        if self.publish_func:
            self.publish_func("CLASS_I", event)
        return True
