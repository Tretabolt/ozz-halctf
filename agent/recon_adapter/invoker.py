"""Stage 2: ProcessInvoker com BoundedReader (<= 70 LOC)"""
import subprocess

class ProcessInvoker:
    def invoke(self, cmd: str, timeout: float = 300.0, max_bytes: int = 10 * 1024 * 1024) -> str:
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, _ = proc.communicate(timeout=timeout)
        if len(out) > max_bytes:
            raise MemoryError("MEMORY_LIMIT_EXCEEDED")
        if proc.returncode != 0:
            raise RuntimeError(f"PROCESS_FAILED: exit_code {proc.returncode}")
        return out.decode("utf-8", errors="ignore")
