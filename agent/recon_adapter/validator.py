"""Stage 1: RequestValidator (<= 70 LOC)"""
from .dtos import ReconRequest

class RequestValidator:
    def __init__(self, max_timeout: float = 600.0, max_memory_mb: int = 1024):
        self.max_timeout = max_timeout
        self.max_memory_mb = max_memory_mb

    def validate(self, request: ReconRequest) -> bool:
        if not request.request_id or not request.target or not request.target.value:
            raise ValueError("INVALID_REQUEST_STRUCTURE")
        if request.hard_timeout > self.max_timeout:
            raise ValueError("RESOURCE_LIMIT_EXCEEDED: Timeout limit")
        if request.memory_limit_mb > self.max_memory_mb:
            raise ValueError("RESOURCE_LIMIT_EXCEEDED: Memory limit")
        return True
