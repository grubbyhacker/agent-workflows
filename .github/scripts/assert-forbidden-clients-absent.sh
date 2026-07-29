#!/usr/bin/env bash
# Run inside the completed agent image.  Only inspect locations from which a
# worker can execute a program: PATH plus the conventional system bin dirs.
set -euo pipefail

forbidden_command_patterns=(
  gh tofu opentofu ansible* doppler ssh ssh-* scp sftp dbclient
)

is_forbidden_name() {
  local name="$1"
  local pattern

  for pattern in "${forbidden_command_patterns[@]}"; do
    [[ "$name" == $pattern ]] && return 0
  done
  return 1
}

fail_forbidden_client() {
  printf 'ERROR: forbidden executable client exists at %s\n' "$1" >&2
  exit 1
}

check_client() {
  local client="$1"
  local resolved_client resolved_name

  [[ -x "$client" ]] || return 0
  if is_forbidden_name "${client##*/}"; then
    fail_forbidden_client "$client"
  fi

  resolved_client="$(readlink -f -- "$client" 2>/dev/null || true)"
  [[ -n "$resolved_client" ]] || return 0
  resolved_name="${resolved_client##*/}"
  if is_forbidden_name "$resolved_name"; then
    fail_forbidden_client "$client"
  fi
}

if command -v dpkg-query >/dev/null 2>&1 \
  && dpkg-query -W -f='${Status}' openssh-client 2>/dev/null | grep -q 'install ok installed'; then
  printf '%s\n' 'ERROR: openssh-client is installed.' >&2
  exit 1
fi

declare -A directories=()
for directory in /bin /sbin /usr/bin /usr/sbin /usr/local/bin /usr/local/sbin; do
  directories["$directory"]=1
done

IFS=: read -r -a path_directories <<< "${PATH:-}"
for directory in "${path_directories[@]}"; do
  [[ -n "$directory" ]] || directory=.
  directories["$directory"]=1
done

for directory in "${!directories[@]}"; do
  [[ -d "$directory" ]] || continue
  while IFS= read -r -d '' client; do
    check_client "$client"
  done < <(find "$directory" -maxdepth 1 \( -type f -o -type l \) -print0)
done
