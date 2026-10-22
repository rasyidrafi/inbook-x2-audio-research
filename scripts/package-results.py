#!/usr/bin/env python3
"""Create explicit source/binary deliverables, excluding vendor binary/decompilation."""
from pathlib import Path
import hashlib
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts"


def files_under(path: Path):
    if path.is_file():
        yield path
    else:
        for candidate in sorted(path.rglob("*")):
            if candidate.is_file() and "__pycache__" not in candidate.parts:
                yield candidate


def main() -> None:
    OUT.mkdir(exist_ok=True)
    selected = [ROOT / name for name in (
        "README.md", "LICENSE", "docs", "module", "patches", "scripts", "tests",
        "inputs/linux-upstream", "inputs/linux-current",
        "analysis/board-config.json", "analysis/inventory-summary.json", "analysis/input-sha256.txt")]
    selected.extend(path for path in sorted((ROOT / "validation").iterdir())
                    if path.suffix in (".log", ".txt", ".md", ".c"))
    with tarfile.open(OUT / "inbook-x2-es8326-source-1.1.0.tar.gz", "w:gz") as archive:
        for entry in selected:
            if not entry.exists():
                raise FileNotFoundError(entry)
            for path in files_under(entry):
                archive.add(path, arcname=Path("inbook-x2-audio-research") / path.relative_to(ROOT))
    with tarfile.open(OUT / "inbook-x2-es8326-modules-1.1.0.tar.gz", "w:gz") as archive:
        for path in files_under(OUT / "modules"):
            archive.add(path, arcname=path.relative_to(OUT))
    hashes = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            hashes.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(OUT)}")
    (OUT / "SHA256SUMS").write_text("\n".join(hashes) + "\n")
    print("Created source archive, binary archive and SHA256SUMS.")


if __name__ == "__main__":
    main()
