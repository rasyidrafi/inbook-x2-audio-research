#!/usr/bin/env python3
"""Copy this laptop's compiler and ELF dependencies for isolated remote use.

Only copies files and inspects ELF dependencies; it does not compile anything.
"""
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "build/toolchain23"
TOOLS = ("clang", "ld.lld", "llvm-ar", "llvm-nm", "llvm-objcopy", "llvm-objdump",
         "llvm-readelf", "llvm-strip", "pahole")


def main() -> None:
    for directory in ("bin", "lib", "wrappers"):
        (DEST / directory).mkdir(parents=True, exist_ok=True)
    inputs = [Path(shutil.which(name) or name) for name in TOOLS]
    # Include the runtime libraries needed by prebuilt kernel build utilities.
    inputs.extend(Path("/usr/lib/modules").glob("*/build/tools/objtool/objtool"))
    inputs.extend(Path("/usr/lib/modules").glob("*/build/scripts/mod/modpost"))
    libraries: set[Path] = set()
    for path in inputs:
        result = subprocess.run(["ldd", str(path)], capture_output=True, text=True, check=True)
        for match in re.finditer(r"(/[^\s()]+)", result.stdout):
            lib = Path(match[1])
            if lib.is_file():
                libraries.add(lib)
    for lib in sorted(libraries):
        shutil.copy2(lib, DEST / "lib" / lib.name, follow_symlinks=True)
    for name in TOOLS:
        shutil.copy2(shutil.which(name), DEST / "bin" / name, follow_symlinks=True)
        wrapper = DEST / "wrappers" / name
        wrapper.write_text('#!/usr/bin/env bash\nset -euo pipefail\n'
            'root="$(cd "$(dirname "$0")/.." && pwd)"\n'
            f'exec "$root/lib/ld-linux-x86-64.so.2" --library-path "$root/lib" '
            f'"$root/bin/{name}" "$@"\n')
        wrapper.chmod(0o755)
    shutil.copytree("/usr/lib/clang", DEST / "lib/clang", dirs_exist_ok=True)
    print(f"Exported exact toolchain to {DEST}")


if __name__ == "__main__":
    main()
