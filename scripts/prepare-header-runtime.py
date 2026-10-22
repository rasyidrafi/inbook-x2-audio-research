#!/usr/bin/env python3
"""Wrap copied header host tools with the copied ELF loader on build-host only.

The kernel headers and module build flags remain unchanged. Original host
executables are retained as *.elf; this affects project-local header copies.
"""
from pathlib import Path
import shlex

root = Path(__file__).resolve().parents[1]
runtime = root / "build/toolchain23/lib"
for kernel in ("7.2.9-2-cachyos", "6.18.55-2-cachyos-lts"):
    base = root / "build/headers" / kernel / "build"
    for relative in ("tools/objtool/objtool", "scripts/mod/modpost"):
        tool = base / relative
        original = tool.with_suffix(".elf")
        if not original.exists():
            if not tool.read_bytes().startswith(b"\x7fELF"):
                raise ValueError(f"Not an ELF binary: {tool}")
            tool.rename(original)
        tool.write_text("#!/usr/bin/env bash\nexec " +
                        shlex.quote(str(runtime / "ld-linux-x86-64.so.2")) +
                        " --library-path " + shlex.quote(str(runtime)) + " " +
                        shlex.quote(str(original)) + ' "$@"\n')
        tool.chmod(0o755)
print("Prepared copied header host tools using isolated runtime.")
