#!/usr/bin/env bash
# Run on build-host, with copies of the laptop's exact kernel build headers.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/modules validation
toolchain="$PWD/build/toolchain23"
"$toolchain/wrappers/clang" --version > validation/compiler.txt
"$toolchain/wrappers/gcc" --version >> validation/compiler.txt
for kernel in 7.2.9-2-cachyos 6.18.55-2-cachyos-lts; do
  target="$PWD/build/modules/$kernel"
  mkdir -p "$target"
  cp module/* "$target/"
  if grep -q '^CONFIG_CC_IS_CLANG=y' "build/headers/$kernel/build/.config"; then
    compiler=(LLVM="$toolchain/wrappers/")
  else
    compiler=(CC="$toolchain/wrappers/gcc" LD="$toolchain/wrappers/ld.bfd"
      AR="$toolchain/wrappers/llvm-ar" NM="$toolchain/wrappers/nm"
      OBJCOPY="$toolchain/wrappers/objcopy" OBJDUMP="$toolchain/wrappers/objdump"
      READELF="$toolchain/wrappers/readelf" STRIP="$toolchain/wrappers/strip")
  fi
  make -C "$target" KDIR="$PWD/build/headers/$kernel/build" \
    "${compiler[@]}" PAHOLE="$toolchain/wrappers/pahole" -j3 \
    2>&1 | tee "validation/build-$kernel.log"
  # Read-only metadata, never load a module on the build host.
  /sbin/modinfo "$target/snd-soc-sof_es8336.ko" > "validation/modinfo-$kernel.txt"
done
