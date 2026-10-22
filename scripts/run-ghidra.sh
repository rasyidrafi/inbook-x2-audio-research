#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/ghidra analysis/decompiled
ghidra_dir=.tools/ghidra_12.2_PUBLIC
chmod +x "$ghidra_dir/support/analyzeHeadless" "$ghidra_dir/support/launch.sh"
find "$ghidra_dir/Ghidra" -path '*/os/linux_x86_64/*' -type f -exec chmod +x {} +
export JAVA_HOME="$PWD/.tools/jdk25"
export PATH="$JAVA_HOME/bin:$PATH"
"$ghidra_dir/support/analyzeHeadless" \
  "$PWD/build/ghidra" es8326-windows \
  -import "$PWD/inputs/windows/ESAuDriverTDMMode.sys" \
  -overwrite -analysisTimeoutPerFile 600 -max-cpu 3 \
  -scriptPath "$PWD/scripts/ghidra" \
  -postScript ExportAudio.java "$PWD/analysis/decompiled" \
  -log "$PWD/analysis/ghidra.log" \
  -scriptlog "$PWD/analysis/ghidra-script.log"
