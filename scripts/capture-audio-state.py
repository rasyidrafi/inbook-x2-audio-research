#!/usr/bin/env python3
"""Read-only snapshot for distinguishing amplifier mute from a stalled PCM.

No playback, recordings, GPIO/register writes, module reloads, or service restarts.
GPIO/kernel logs may be unavailable without root; missing access is recorded.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time


def read(path: Path) -> str:
    try:
        return path.read_text()
    except OSError as error:
        return f"UNAVAILABLE: {error}"


def command(args: list[str]) -> dict[str, str | int]:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=10)
        return {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"exit_code": -1, "stderr": str(error)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New JSON output file; existing files are not overwritten")
    args = parser.parse_args()
    result: dict[str, object] = {
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "kernel": command(["uname", "-r"]),
        "loaded_machine_version": read(Path("/sys/module/snd_soc_sof_es8336/version")),
        "cards": read(Path("/proc/asound/cards")),
        "default_sink": command(["wpctl", "inspect", "@DEFAULT_AUDIO_SINK@"]),
    }
    samples: list[dict[str, object]] = []
    for index in range(3):
        samples.append({
            "monotonic_seconds": time.monotonic(),
            "pcm": {str(path): read(path) for path in sorted(
                Path("/proc/asound").glob("card*/pcm*p/sub*/status"))},
            "gpio": read(Path("/sys/kernel/debug/gpio")),
        })
        if index < 2:
            time.sleep(0.5)
    result["samples"] = samples
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(f"Saved read-only snapshot to {args.output}")


if __name__ == "__main__":
    main()
