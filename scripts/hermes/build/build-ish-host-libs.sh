#!/usr/bin/env bash
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
#
# Build iSH's Xcode-defined iOS host-interop libraries with Linux Clang/LLD.
set -euo pipefail

ISH_SOURCE=${1:?pinned iSH source tree}
MESON_BUILD_DIR=${2:?Linux Meson build directory}
OUTPUT_DIR=${3:?directory for iSH framework link inputs}
CC=${CC:-clang}
LLVM_AR=${LLVM_AR:-llvm-ar}
LLVM_RANLIB=${LLVM_RANLIB:-llvm-ranlib}

fail() {
  echo "build-ish-host-libs.sh: $*" >&2
  exit 2
}

[ -d "$ISH_SOURCE/deps/linux" ] || fail "missing initialized iSH Linux kernel submodule"
[ -f "$ISH_SOURCE/deps/linux/arch/ish/kernel/sections.S" ] || fail "missing pinned iSH Mach-O section anchors"
for archive in \
  "$MESON_BUILD_DIR/deps/liblinux.a" \
  "$MESON_BUILD_DIR/libdocumentsfs_module.a" \
  "$MESON_BUILD_DIR/libfakefs.a" \
  "$MESON_BUILD_DIR/libish_emu.a"; do
  [ -s "$archive" ] || fail "missing Linux Meson archive: $archive"
done
command -v "$CC" >/dev/null 2>&1 || fail "Clang compiler not found: $CC"
command -v "$LLVM_AR" >/dev/null 2>&1 || fail "LLVM archiver not found: $LLVM_AR"
command -v "$LLVM_RANLIB" >/dev/null 2>&1 || fail "LLVM ranlib not found: $LLVM_RANLIB"

mkdir -p "$OUTPUT_DIR"
BUILD_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ish-host-libs.XXXXXX")
trap 'rm -rf "$BUILD_DIR"' EXIT

KERNEL_INCLUDES=(
  -I"$ISH_SOURCE/app"
  -I"$ISH_SOURCE"
  -I"$ISH_SOURCE/deps/linux/arch/ish/include"
  -I"$MESON_BUILD_DIR/deps/linux/arch/ish/include/generated"
  -I"$ISH_SOURCE/deps/linux/include"
  -I"$MESON_BUILD_DIR/deps/linux/include"
  -I"$ISH_SOURCE/deps/linux/arch/ish/include/uapi"
  -I"$MESON_BUILD_DIR/deps/linux/arch/ish/include/generated/uapi"
  -I"$ISH_SOURCE/deps/linux/include/uapi"
)
KERNEL_FLAGS=(
  -D__KERNEL__
  -U__weak
  -include linux/kconfig.h
  -include linux/compiler_types.h
  -fblocks
  -Wno-gnu-variable-sized-type-not-at-end
  -Wno-conditional-uninitialized
)

build_archive() {
  local archive_name=$1
  shift
  local object_dir="$BUILD_DIR/${archive_name%.a}"
  mkdir -p "$object_dir"
  local objects=()
  local index=0
  for source in "$@"; do
    local object="$object_dir/$index-$(basename "$source").o"
    "$CC" "${KERNEL_INCLUDES[@]}" "${KERNEL_FLAGS[@]}" -c "$source" -o "$object"
    objects+=("$object")
    index=$((index + 1))
  done
  "$LLVM_AR" rcs "$object_dir/$archive_name" "${objects[@]}"
  "$LLVM_RANLIB" "$object_dir/$archive_name"
  cp "$object_dir/$archive_name" "$OUTPUT_DIR/$archive_name"
}

build_archive libiSHLinux.a \
  "$ISH_SOURCE/app/LinuxInterop.c" \
  "$ISH_SOURCE/app/PasteboardDeviceLinux.c" \
  "$ISH_SOURCE/linux/fakefs.c" \
  "$ISH_SOURCE/app/LinuxRoot.c" \
  "$ISH_SOURCE/app/LinuxTTY.c" \
  "$ISH_SOURCE/app/LinuxPTY.c"

USER_INCLUDES=(
  -I"$ISH_SOURCE/deps/linux/arch/ish/include"
  -I"$ISH_SOURCE/deps/linux/include"
  -I"$MESON_BUILD_DIR/deps/linux/include"
  -I"$ISH_SOURCE"
)
USER_OBJECT="$BUILD_DIR/libiSHLinuxUser/emu_asbestos.o"
mkdir -p "$(dirname "$USER_OBJECT")"
"$CC" "${USER_INCLUDES[@]}" \
  -include user.h -include linux/kconfig.h \
  -c "$ISH_SOURCE/linux/emu_asbestos.c" -o "$USER_OBJECT"
"$LLVM_AR" rcs "$BUILD_DIR/libiSHLinuxUser.a" "$USER_OBJECT"
"$LLVM_RANLIB" "$BUILD_DIR/libiSHLinuxUser.a"
cp "$BUILD_DIR/libiSHLinuxUser.a" "$OUTPUT_DIR/libiSHLinuxUser.a"

cp "$MESON_BUILD_DIR/deps/liblinux.a" "$OUTPUT_DIR/liblinux.a"
cp "$MESON_BUILD_DIR/libdocumentsfs_module.a" "$OUTPUT_DIR/libdocumentsfs_module.a"
cp "$MESON_BUILD_DIR/libfakefs.a" "$OUTPUT_DIR/libfakefs.a"
cp "$MESON_BUILD_DIR/libish_emu.a" "$OUTPUT_DIR/libish_emu.a"
cp "$ISH_SOURCE/app/LinuxInterop.h" "$OUTPUT_DIR/LinuxInterop.h"
"$CC" -c "$ISH_SOURCE/deps/linux/arch/ish/kernel/sections.S" \
  -o "$OUTPUT_DIR/ish-sections.o"

for input in \
  "$OUTPUT_DIR/libiSHLinux.a" \
  "$OUTPUT_DIR/libiSHLinuxUser.a" \
  "$OUTPUT_DIR/liblinux.a" \
  "$OUTPUT_DIR/libdocumentsfs_module.a" \
  "$OUTPUT_DIR/libfakefs.a" \
  "$OUTPUT_DIR/libish_emu.a" \
  "$OUTPUT_DIR/ish-sections.o" \
  "$OUTPUT_DIR/LinuxInterop.h"; do
  [ -s "$input" ] || fail "failed to produce framework input: $input"
done

echo "Built Linux iSH host-interoperability archives and section anchors in $OUTPUT_DIR"
