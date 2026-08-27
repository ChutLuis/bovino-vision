#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

is_jdk17() {
  local candidate="$1"
  [[ -x "$candidate/bin/java" && -x "$candidate/bin/javac" ]] || return 1
  [[ "$("$candidate/bin/java" -version 2>&1)" == *'"17.'* ]]
}

resolve_jdk17() {
  local candidate
  local candidates=(
    "${JDK_17_HOME:-}"
    "${JAVA_HOME:-}"
    "/usr/lib/jvm/java-17-openjdk"
    /usr/lib/jvm/java-17-openjdk-*
    "$HOME/.jdks/temurin-17"
    "$HOME/.local/share/jdks/temurin-17"
    "$HOME/.sdkman/candidates/java/current"
  )

  for candidate in "${candidates[@]}"; do
    if [[ -n "$candidate" ]] && is_jdk17 "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

if ! java_home="$(resolve_jdk17)"; then
  cat >&2 <<'EOF'
No se encontro un JDK 17 completo (java y javac).
En Nobara/Fedora: sudo dnf install java-17-openjdk-devel
Despues exporte JDK_17_HOME o JAVA_HOME apuntando al JDK 17.
EOF
  exit 1
fi

android_home="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Android/Sdk}}"
adb="$android_home/platform-tools/adb"

if [[ ! -x "$adb" ]]; then
  printf 'No se encontro adb en ANDROID_HOME: %s\n' "$android_home" >&2
  exit 1
fi

if ! "$adb" get-state >/dev/null 2>&1; then
  printf 'No hay un dispositivo Android autorizado. Conecte el A25 y ejecute: %s devices\n' "$adb" >&2
  exit 1
fi

export JAVA_HOME="$java_home"
export ANDROID_HOME="$android_home"
export ANDROID_SDK_ROOT="$android_home"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$PATH"

cd "$project_root"
exec npx expo run:android --device "$@"
