from __future__ import annotations

import asyncio
from typing import Dict, List, Tuple


def _truncate(data: bytes, max_bytes: int) -> Tuple[bytes, bool]:
    if max_bytes <= 0 or len(data) <= max_bytes:
        return data, False
    return data[:max_bytes], True


async def run_command(cmd: List[str], timeout: int, max_output_bytes: int) -> Dict[str, object]:
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        return {"rc": 127, "stdout": "", "stderr": f"command not found: {cmd[0]}"}
    except Exception as exc:
        return {"rc": -1, "stdout": "", "stderr": str(exc)}

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return {"rc": -1, "stdout": "", "stderr": f"timeout after {timeout}s"}

    stdout = stdout or b""
    stderr = stderr or b""

    stdout, out_trunc = _truncate(stdout, max_output_bytes)
    stderr, err_trunc = _truncate(stderr, max_output_bytes)

    stdout_text = stdout.decode("utf-8", errors="replace")
    stderr_text = stderr.decode("utf-8", errors="replace")

    if out_trunc:
        stdout_text += f"\n[output truncated at {max_output_bytes} bytes]"
    if err_trunc:
        stderr_text += f"\n[output truncated at {max_output_bytes} bytes]"

    return {
        "rc": proc.returncode,
        "stdout": stdout_text,
        "stderr": stderr_text,
    }

