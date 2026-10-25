"""Безопасный запуск Python-кода ученика.

Кроссплатформенно: на Linux/macOS используются POSIX-лимиты (resource,
setsid, unshare). На Windows эти механизмы недоступны, поэтому:
  * лимиты CPU/AS/FSIZE/NPROC не устанавливаются,
  * `unshare` не используется,
  * остаётся базовый таймаут через `subprocess.run(timeout=...)`
    и изолированный режим `python -I -S`.

Для промышленной эксплуатации — Docker-раннер на Linux.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

# resource — POSIX-only
try:
    import resource  # type: ignore
    _HAS_RESOURCE = True
except ImportError:  # Windows
    resource = None  # type: ignore
    _HAS_RESOURCE = False

_IS_WINDOWS = os.name == "nt"
_HAS_UNSHARE = (not _IS_WINDOWS) and shutil.which("unshare") is not None


@dataclass
class RunResult:
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    verdict: str = "OK"          # OK|TLE|RE
    execution_ms: float = 0.0
    extra_files: dict[str, str] = field(default_factory=dict)


def _preexec_linux(timeout: float, memory_mb: int):
    def _set():
        try:
            cpu = int(timeout) + 1
            resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
            mem = memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
            resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            os.setsid()
        except Exception:
            pass
    return _set


def _preexec_windows():
    # На Windows preexec_fn запрещён в subprocess.run — возвращаем None.
    return None


def run_python(
    code: str,
    stdin_data: str = "",
    *,
    timeout: float = 5.0,
    memory_mb: int = 128,
    files: dict[str, str] | None = None,
) -> RunResult:
    workdir = tempfile.mkdtemp(prefix="run_")
    try:
        script = Path(workdir, "solution.py")
        script.write_text(code, encoding="utf-8", newline="")

        if files:
            for name, content in files.items():
                safe = os.path.basename(name)  # запрет ../
                Path(workdir, safe).write_text(content, encoding="utf-8", newline="")

        env = {
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "HOME": workdir,
            "TMPDIR": workdir,
            "PATH": os.environ.get("PATH", ""),
        }

        cmd = [sys.executable, "-I", "-S", str(script)]
        if _HAS_UNSHARE:
            cmd = ["unshare", "-rn", "-p", "-f", "--"] + cmd

        preexec = _preexec_linux(timeout, memory_mb) if _HAS_RESOURCE else None
        extra_kwargs: dict = {}
        if not _IS_WINDOWS:
            extra_kwargs["start_new_session"] = True
        if preexec is not None:
            extra_kwargs["preexec_fn"] = preexec

        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                input=stdin_data,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                cwd=workdir,
                env=env,
                **extra_kwargs,
            )
        except subprocess.TimeoutExpired:
            return RunResult(verdict="TLE",
                             execution_ms=(time.perf_counter() - t0) * 1000)
        elapsed = (time.perf_counter() - t0) * 1000

        if proc.returncode != 0:
            return RunResult(
                stdout=proc.stdout or "",
                stderr=proc.stderr or "",
                returncode=proc.returncode,
                verdict="RE",
                execution_ms=elapsed,
            )
        return RunResult(stdout=proc.stdout or "", stderr=proc.stderr or "",
                         returncode=0, verdict="OK", execution_ms=elapsed)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)