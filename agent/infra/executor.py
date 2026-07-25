"""Adaptador de Infraestrutura: SafeProcessExecutor (shell=False) (<= 70 LOC)"""
import subprocess
import shlex
from typing import List
from ..ports.executor import ProcessExecutorPort
from ..dtos.domain_dtos import CommandSpec, ExecutionResult

class SafeProcessExecutor(ProcessExecutorPort):
    """Adaptador de infraestrutura seguro com execv (shell=False) e sanitização."""

    def execute(self, spec: CommandSpec) -> ExecutionResult:
        # Sanitização e montagem do vetor de argumentos (sem shell interpolation)
        safe_args = [spec.binary] + [shlex.quote(arg) for arg in spec.args]
        try:
            proc = subprocess.Popen(
                safe_args,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = proc.communicate(timeout=spec.timeout)
            out_str = stdout.decode("utf-8", errors="ignore")
            err_str = stderr.decode("utf-8", errors="ignore")
            return ExecutionResult(
                output=out_str if proc.returncode == 0 else err_str,
                exit_code=proc.returncode,
                success=(proc.returncode == 0),
                error=err_str if proc.returncode != 0 else None
            )
        except Exception as e:
            return ExecutionResult(output="", exit_code=1, success=False, error=str(e))
