"""Verify the shipped series applies to pinned source and reproduces the module."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PatchSeries(unittest.TestCase):
    def test_patch_series_reproduces_modern_candidate(self):
        with tempfile.TemporaryDirectory(prefix="es8326-patches-") as directory:
            target = Path(directory) / "sound/soc/intel/boards/sof_es8336.c"
            target.parent.mkdir(parents=True)
            target.write_bytes((ROOT / "inputs/linux-upstream/sof_es8336.c").read_bytes())
            for name in (ROOT / "patches/series").read_text().splitlines():
                subprocess.run(["patch", "--batch", "--fuzz=0", "-p1", "-i",
                                str(ROOT / "patches" / name)], cwd=directory,
                               capture_output=True, check=True)
            self.assertEqual(target.read_bytes(),
                             (ROOT / "module/sof_es8336_modern.c").read_bytes())


if __name__ == "__main__":
    unittest.main()
