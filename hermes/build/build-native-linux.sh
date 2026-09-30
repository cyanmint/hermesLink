#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BUILD_ROOT=${BUILD_ROOT:-$ROOT/build/native-linux}
CPYTHON_REPOSITORY=${CPYTHON_REPOSITORY:-https://github.com/holzschu/cpython.git}
CPYTHON_REF=${CPYTHON_REF:-0c3aa6418f2f8d874e1be62e45226af002bbcc8d}
CPYTHON_ROOT=${CPYTHON_ROOT:-$BUILD_ROOT/cpython}
TARGET_ROOT=$BUILD_ROOT/target-cpython
ARTIFACT_ROOT=${ARTIFACT_ROOT:-$ROOT/build/linux-runtime}
HOST_PYTHON=${HOST_PYTHON:-$(command -v python3.13 || command -v python3)}
JOBS=${JOBS:-$(getconf _NPROCESSORS_ONLN)}

mkdir -p "$BUILD_ROOT" "$ARTIFACT_ROOT"
if [ ! -d "$CPYTHON_ROOT/.git" ]; then
  rm -rf "$CPYTHON_ROOT"
  git clone --filter=blob:none --no-checkout --depth=1 "$CPYTHON_REPOSITORY" "$CPYTHON_ROOT"
else
  git -C "$CPYTHON_ROOT" remote set-url origin "$CPYTHON_REPOSITORY"
fi
git -C "$CPYTHON_ROOT" fetch --depth=1 origin "$CPYTHON_REF"
git -C "$CPYTHON_ROOT" checkout --detach FETCH_HEAD

if [ ! -f "$TARGET_ROOT/Makefile" ] ||
   [ "$(cat "$TARGET_ROOT/.hermes-cpython-ref" 2>/dev/null || true)" != "$CPYTHON_REF" ]; then
  rm -rf "$TARGET_ROOT"
  mkdir -p "$TARGET_ROOT"
  git -C "$CPYTHON_ROOT" archive HEAD | tar -x -C "$TARGET_ROOT"
  (
    cd "$TARGET_ROOT"
    CPPFLAGS="${CPPFLAGS:-}" \
    LDFLAGS="${LDFLAGS:-}" \
      ./configure --prefix="$BUILD_ROOT/install" --disable-shared \
        --with-openssl=/usr --with-openssl-rpath=no \
        --without-ensurepip --disable-test-modules --with-lto=no
  )
  printf '%s\n' "$CPYTHON_REF" > "$TARGET_ROOT/.hermes-cpython-ref"
fi

python3 - "$ROOT/build" "$TARGET_ROOT/Modules/Setup.stdlib" \
  "$TARGET_ROOT/Modules/Setup.local" "$TARGET_ROOT/Makefile" <<'PY'
import pathlib
import sys

sys.path.insert(0, sys.argv[1])
from configure_native_modules import ensure_required_static_modules, module_object_paths

source, target, makefile = map(pathlib.Path, sys.argv[2:])
lines = source.read_text(encoding="utf-8").splitlines()
for index, line in enumerate(lines):
    if line.strip() == "*shared*":
        lines[index] = "*static*"
    if line.startswith("_decimal "):
        lines[index] += " -IModules/_decimal/libmpdec Modules/_decimal/libmpdec/libmpdec.a"
lines = ensure_required_static_modules(lines)
target.write_text("\n".join(lines) + "\n", encoding="utf-8")
objects = module_object_paths(lines)
(makefile.parent / "native-module-objects.txt").write_text(
    "\n".join(objects) + "\n", encoding="utf-8"
)
PY

(cd "$TARGET_ROOT" && make -n -o Makefile libpython3.13.a > native-libpython-dryrun.txt)
python3 - "$TARGET_ROOT/native-libpython-dryrun.txt" \
  "$TARGET_ROOT/native-module-objects.txt" <<'PY'
from pathlib import Path
import re
import shlex
import sys

dryrun, output = map(Path, sys.argv[1:])
objects = set()
for line in dryrun.read_text(encoding="utf-8", errors="replace").splitlines():
    if "libpython3.13.a" not in line or " rcs " not in f" {line} ":
        continue
    tokens = shlex.split(line)
    try:
        index = tokens.index("libpython3.13.a")
    except ValueError:
        continue
    objects.update(token for token in tokens[index + 1:] if token.endswith(".o"))
makefile = dryrun.parent / "Makefile"
lines = makefile.read_text(encoding="utf-8", errors="replace").splitlines()
for index, line in enumerate(lines):
    if not re.match(r"^\s*MODOBJS\s*=", line):
        continue
    value = line.split("=", 1)[1]
    cursor = index + 1
    while value.rstrip().endswith("\\") and cursor < len(lines):
        value = value.rstrip()[:-1] + " " + lines[cursor]
        cursor += 1
    objects.update(token for token in value.split() if token.endswith(".o"))
objects.update(
    token
    for token in output.read_text(encoding="utf-8").splitlines()
    if token.endswith(".o")
)
if not objects:
    raise SystemExit("could not extract libpython object list from Makefile dry-run")
output.write_text("\n".join(sorted(objects)) + "\n", encoding="utf-8")
PY

(cd "$TARGET_ROOT" && make -o Makefile -o Modules/config.c -o Modules/config.h \
  -j"$JOBS" $(cat native-module-objects.txt) \
  Modules/binascii.o Modules/_struct.o Modules/socketmodule.o Modules/selectmodule.o \
  Modules/mathmodule.o Modules/cmathmodule.o Modules/_contextvarsmodule.o \
  Modules/arraymodule.o Modules/_randommodule.o \
  Modules/_decimal/libmpdec/libmpdec.a \
  Modules/_hacl/libHacl_Hash_SHA2.a Modules/expat/libexpat.a)

(cd "$TARGET_ROOT" &&
  find Modules -type f -name '*.o' -print >> native-module-objects.txt &&
  sort -u native-module-objects.txt |
    grep -v '^Modules/_hacl/Hacl_Hash_SHA2\.o$' |
    grep -v '^Modules/expat/' > native-module-objects.filtered &&
  printf '%s\n' Modules/binascii.o Modules/selectmodule.o \
    Modules/_contextvarsmodule.o Modules/arraymodule.o Modules/_randommodule.o \
    >> native-module-objects.filtered &&
  sort -u native-module-objects.filtered > native-module-objects.txt)

python3 "$ROOT/build/generate-native-module-registry.py" \
  "$TARGET_ROOT/native-module-objects.txt" "$TARGET_ROOT" "$BUILD_ROOT/native_modules.c"
(cd "$TARGET_ROOT" &&
  cc -I. -IInclude -c "$BUILD_ROOT/native_modules.c" -o native_modules.o &&
  printf '%s\n' native_modules.o >> native-module-objects.txt &&
  sort -u native-module-objects.txt -o native-module-objects.txt &&
  ar rcs libpython3.13.a $(cat native-module-objects.txt) &&
  ranlib libpython3.13.a)

if [ "${HERMES_BUILD_RUNTIME_ZIP:-1}" = "1" ]; then
  BUILD_ROOT="$BUILD_ROOT" HOST_PYTHON="$HOST_PYTHON" \
    bash "$ROOT/build/build-hermesrt-zip.sh" "$CPYTHON_ROOT" "$ARTIFACT_ROOT/hermesrt.zip"
fi

cc -I"$TARGET_ROOT" -I"$TARGET_ROOT/Include" \
  "$ROOT/overlay/cpython/Programs/hermes_main.c" \
  "$TARGET_ROOT/libpython3.13.a" \
  "$TARGET_ROOT/Modules/_decimal/libmpdec/libmpdec.a" \
  "$TARGET_ROOT/Modules/_hacl/libHacl_Hash_SHA2.a" \
  "$TARGET_ROOT/Modules/expat/libexpat.a" \
  -static -lssl -lcrypto -lsqlite3 -lz -lbz2 -llzma -lreadline \
  -lpanelw -lncursesw -ltinfo -lgdbm_compat -lgdbm -lffi -luuid -lcrypt \
  -lutil -lm -ldl -lpthread \
  -o "$ARTIFACT_ROOT/hermes"

test -x "$ARTIFACT_ROOT/hermes"
file "$ARTIFACT_ROOT/hermes"
if [ "${HERMES_BUILD_RUNTIME_ZIP:-1}" = "1" ]; then
  test -s "$ARTIFACT_ROOT/hermesrt.zip"
fi
