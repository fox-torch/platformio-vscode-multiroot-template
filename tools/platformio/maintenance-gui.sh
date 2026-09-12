#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This launcher supports macOS only." >&2
  exit 1
fi

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
maintenance="$script_dir/maintenance.py"
action="${1:-menu}"
python_bin="$HOME/.platformio/penv/bin/python"
if [[ ! -x "$python_bin" ]]; then
  python_bin="$(command -v python3 || true)"
fi
if [[ -z "$python_bin" ]]; then
  osascript -e 'display alert "Python not found" message "Install PlatformIO IDE first." as critical'
  exit 1
fi

show_message() {
  local title="$1" message="$2"
  osascript - "$title" "$message" <<'APPLESCRIPT'
on run argv
  display dialog (item 2 of argv) with title (item 1 of argv) buttons {"OK"} default button "OK"
end run
APPLESCRIPT
}
choose_folder() {
  local prompt="$1" default_path="$2"
  osascript - "$prompt" "$default_path" <<'APPLESCRIPT'
on run argv
  set promptText to item 1 of argv
  set defaultPath to POSIX file (item 2 of argv)
  return POSIX path of (choose folder with prompt promptText default location defaultPath)
end run
APPLESCRIPT
}

run_tool() {
  local success="$1"
  shift
  local log_dir="$repo_root/.pio/maintenance"
  local log_path="$log_dir/last.log"
  mkdir -p "$log_dir"
  set +e
  local output
  output="$($python_bin "$maintenance" --repo-root "$repo_root" "$@" 2>&1)"
  local status=$?
  set -e
  printf '%s\n' "$output" > "$log_path"
  if [[ $status -eq 0 ]]; then
    show_message "PlatformIO Maintenance" "$success\n\nLog: $log_path"
  else
    local tail_output
    tail_output="$(printf '%s\n' "$output" | tail -n 18)"
    show_message "PlatformIO Maintenance" "Operation failed.\n\n$tail_output\n\nLog: $log_path"
  fi
  return $status
}
repair_gui() {
  local project
  project="$(choose_folder 'Select a PlatformIO project to repair.' "$repo_root")"
  project="${project%/}"
  run_tool 'Repair completed.' repair "$project"
}

import_gui() {
  local source destination
  source="$(choose_folder 'Select an external PlatformIO project to import.' "$HOME")"
  source="${source%/}"
  destination="$(choose_folder 'Select the destination parent under projects/.' "$repo_root/projects")"
  destination="${destination%/}"
  run_tool 'Import and validation completed.' import "$source" "$destination"
}

repair_all_gui() {
  local answer
  answer="$(osascript -e 'button returned of (display dialog "Rebuild every PlatformIO project from clean generated state?" with title "PlatformIO Repair All" buttons {"Cancel", "Run"} default button "Run" cancel button "Cancel")' 2>/dev/null || true)"
  [[ "$answer" == "Run" ]] || return 0
  run_tool 'Repair all completed.' repair-all
}

if [[ "$action" == "menu" ]]; then
  action="$(osascript -e 'choose from list {"Repair project", "Import project", "Repair all projects"} with title "PlatformIO Maintenance" with prompt "Use only for recovery or migration."' | tr -d '{}')"
  case "$action" in
    'Repair project') action='repair' ;;
    'Import project') action='import' ;;
    'Repair all projects') action='repair-all' ;;
    *) exit 0 ;;
  esac
fi
case "$action" in
  repair) repair_gui ;;
  import) import_gui ;;
  repair-all) repair_all_gui ;;
  *) echo "Unknown action: $action" >&2; exit 2 ;;
esac
