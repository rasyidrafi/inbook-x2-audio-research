#!/usr/bin/env python3
"""Export the exact GCC/binutils used by the installed LTS kernel; no build."""
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

root = Path(__file__).resolve().parents[1]
dest = root / "build/toolchain23"
names = ("gcc", "as", "ld.bfd", "nm", "objcopy", "objdump", "readelf", "strip")
programs = {name: Path(shutil.which(name)) for name in names}
programs["cc1"] = Path(subprocess.check_output(["gcc", "-print-prog-name=cc1"], text=True).strip())
files: set[Path] = set()
for name, path in programs.items():
    binary = dest / "bin" / name
    shutil.copy2(path, binary, follow_symlinks=True)
    files.add(binary)
    for lib in re.findall(r"(/[^\s()]+)", subprocess.check_output(["ldd", str(path)], text=True)):
        if Path(lib).is_file():
            copied = dest / "lib" / Path(lib).name
            shutil.copy2(lib, copied, follow_symlinks=True)
            files.add(copied)
    wrapper = dest / "wrappers" / name
    extra = ' -B"$root/wrappers/" -B"$root/gcc/"' if name == "gcc" else ""
    wrapper.write_text('#!/usr/bin/env bash\nset -euo pipefail\n'
        'root="$(cd "$(dirname "$0")/.." && pwd)"\n'
        f'exec "$root/lib/ld-linux-x86-64.so.2" --library-path "$root/lib" '
        f'"$root/bin/{name}"{extra} "$@"\n')
    wrapper.chmod(0o755)
    files.add(wrapper)
include = Path(subprocess.check_output(["gcc", "-print-file-name=include"], text=True).strip())
shutil.copytree(include, dest / "gcc/include", dirs_exist_ok=True)
files.add(dest / "gcc/include")
with tarfile.open(root / "build/gcc-runtime.tar.gz", "w:gz") as archive:
    for path in sorted(files):
        archive.add(path, arcname=path.relative_to(dest))
print("Exported GCC, assembler, linker, builtin headers and runtime libraries.")
