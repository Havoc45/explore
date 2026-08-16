#!/usr/bin/env bash
#
# bump-version.sh — keep the version in lockstep across every declared manifest.
#
# Adapted from the superpowers plugin's bump-version.sh
# (MIT © Jesse Vincent, https://github.com/obra/superpowers — see NOTICE §4).
# Rewritten to need only python3 + perl (no jq), and to support the
# YAML-frontmatter version field in skills/explore/SKILL.md.
#
# Usage:
#   scripts/bump-version.sh <new-version>   Bump all declared files to X.Y.Z
#   scripts/bump-version.sh --check         Show current versions, detect drift
#   scripts/bump-version.sh --audit         Check + scan repo for stray version strings
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG="$REPO_ROOT/.version-bump.json"

[[ -f "$CONFIG" ]] || { echo "error: .version-bump.json not found at $CONFIG" >&2; exit 1; }

# --- helpers ---

# The single source of truth for the version format. Both the bump path (which
# validates the NEW version) and the check path (which validates every value it
# reads back) go through is_valid_version, so the two can never drift apart.
# A future format change (pre-release tags?) happens here once.
VERSION_RE='^[0-9]+\.[0-9]+\.[0-9]+$'

is_valid_version() {
  [[ "$1" =~ $VERSION_RE ]]
}

# Read the version from a declared file. JSON files are parsed properly
# (dotted field paths, numeric segments = array indices); .md files read the
# first `version: "X.Y.Z"` line of their YAML frontmatter.
read_field() {
  python3 - "$1" "$2" <<'PY'
import json, re, sys
path, field = sys.argv[1], sys.argv[2]
if path.endswith(".md"):
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r'\s*version:\s*"([^"]+)"', line)
            if m:
                print(m.group(1))
                break
else:
    obj = json.load(open(path, encoding="utf-8"))
    for part in field.split("."):
        obj = obj[int(part)] if part.isdigit() else obj[part]
    print(obj)
PY
}

# Write the version into a declared file, format-preserving: replace only the
# FIRST version key in the file (every declared file carries exactly one —
# cmd_bump re-reads the declared field after writing and fails loudly if the
# first match was a different key). For .md files, handling is extension-based:
# the first `version: "X.Y.Z"` line is treated as the frontmatter version, so
# the frontmatter version must stay the first such line in the file.
write_field() {
  local file="$1" ver="$2"
  if [[ "$file" == *.md ]]; then
    perl -0pi -e 's/(version:\s*")[0-9]+\.[0-9]+\.[0-9]+[^"]*(")/${1}'"$ver"'${2}/' "$file"
  else
    perl -0pi -e 's/("version"\s*:\s*")[0-9]+\.[0-9]+\.[0-9]+[^"]*(")/${1}'"$ver"'${2}/' "$file"
  fi
}

# Lines of "path<TAB>field" from the config.
declared_files() {
  python3 -c 'import json,sys; [print(f["path"], f["field"], sep="\t") for f in json.load(open(sys.argv[1]))["files"]]' "$CONFIG"
}

# Report-only drift check: print a WARNING when the manifests' description
# strings are not all identical after trimming whitespace. Never affects the
# exit code — audit's version-string semantics are unchanged.
check_description_drift() {
  python3 - "$REPO_ROOT" <<'PY'
import json, sys
root = sys.argv[1]
mans = [
    (".claude-plugin/plugin.json", "description"),
    (".claude-plugin/marketplace.json", "plugins.0.description"),
    (".codex-plugin/plugin.json", "description"),
    (".cursor-plugin/plugin.json", "description"),
    (".kimi-plugin/plugin.json", "description"),
    ("gemini-extension.json", "description"),
    ("package.json", "description"),
]
descs = {}
for path, field in mans:
    try:
        obj = json.load(open(f"{root}/{path}", encoding="utf-8"))
        for part in field.split("."):
            obj = obj[int(part)] if part.isdigit() else obj[part]
        descs[path] = obj.strip()
    except Exception as e:
        descs[path] = f"<unreadable: {e}>"
uniq = set(descs.values())
if len(uniq) > 1:
    print("WARNING: manifest description drift — the 7 manifests' description strings are not all identical (report-only; audit exit code unchanged):")
    for path, d in descs.items():
        print(f"  {path}: {d[:80]}{'...' if len(d) > 80 else ''}")
else:
    print("Manifest descriptions: all 7 identical.")
PY
}

audit_excludes() {
  python3 -c 'import json,sys; [print(p) for p in json.load(open(sys.argv[1])).get("audit",{}).get("exclude",[])]' "$CONFIG"
}

validate_config_paths() {
  local path
  while IFS=$'\t' read -r path _; do
    if [[ "$path" == /* || "$path" == *..* ]]; then
      echo "error: unsafe path in config: $path" >&2
      exit 1
    fi
  done < <(declared_files)
}

# --- commands ---

cmd_check() {
  local has_drift=0
  local versions=()
  local labels=()

  validate_config_paths

  echo "Version check:"
  echo ""

  while IFS=$'\t' read -r path field; do
    local fullpath="$REPO_ROOT/$path"
    if [[ ! -f "$fullpath" ]]; then
      printf "  %-50s  MISSING\n" "$path ($field)"
      has_drift=1
      continue
    fi
    # Check the read explicitly — do NOT lean on `set -e`. cmd_audit calls
    # cmd_check inside an `||` list, which disables errexit for this whole
    # function, so a failed read would otherwise flow on as an empty string and
    # be counted as a version. A failed read OR empty output is UNREADABLE,
    # handled exactly like a MISSING file: reported, drift, not collected.
    local ver
    if ! ver=$(read_field "$fullpath" "$field") || [[ -z "$ver" ]]; then
      printf "  %-50s  UNREADABLE\n" "$path ($field)"
      has_drift=1
      continue
    fi
    printf "  %-50s  %s\n" "$path ($field)" "$ver"
    versions+=("$ver")
    labels+=("$path ($field)")
  done < <(declared_files)

  echo ""

  if [[ ${#versions[@]} -eq 0 ]]; then
    echo "error: no declared files readable — wrong repo?" >&2
    return 1
  fi

  # Distinctness alone is not sync: eight files agreeing on a garbage string is
  # not a healthy repo. Validate every value against the same rule cmd_bump
  # enforces on the way in.
  local -a invalid=()
  local i
  for i in "${!versions[@]}"; do
    is_valid_version "${versions[i]}" || invalid+=("  ${labels[i]} -> ${versions[i]}")
  done
  if [[ ${#invalid[@]} -gt 0 ]]; then
    echo "INVALID VERSION VALUES — expected X.Y.Z:"
    printf '%s\n' "${invalid[@]}"
    echo ""
    has_drift=1
  fi

  local unique
  unique=$(printf '%s\n' "${versions[@]}" | sort -u | wc -l | tr -d ' ')
  if [[ "$unique" -gt 1 ]]; then
    echo "DRIFT DETECTED — versions are not in sync:"
    printf '%s\n' "${versions[@]}" | sort | uniq -c | sort -rn
    has_drift=1
  elif [[ ${#invalid[@]} -eq 0 ]]; then
    echo "All declared files are in sync at ${versions[0]}"
  fi

  return $has_drift
}

cmd_audit() {
  local check_status=0
  cmd_check || check_status=$?
  echo ""

  # Current version = most common across declared files
  local current_version
  current_version=$(
    while IFS=$'\t' read -r path field; do
      local fullpath="$REPO_ROOT/$path"
      [[ -f "$fullpath" ]] && read_field "$fullpath" "$field"
    done < <(declared_files) | sort | uniq -c | sort -rn | head -1 | awk '{print $2}'
  )

  if [[ -z "$current_version" ]]; then
    echo "error: could not determine current version" >&2
    return 1
  fi

  echo "Audit: scanning repo for version string '$current_version'..."
  echo ""

  # Config exclude patterns split by shape: grep's --exclude/--exclude-dir match
  # basenames only, so a pattern containing "/" (e.g. ".claude/worktrees/" where
  # executor worktrees hold full repo copies) is instead applied as a
  # repo-relative path prefix filter on the matches after the scan.
  local -a exclude_args=() exclude_prefixes=()
  while IFS= read -r pattern; do
    if [[ "$pattern" == */* ]]; then
      exclude_prefixes+=("${pattern%/}/")
    else
      exclude_args+=("--exclude=$pattern" "--exclude-dir=$pattern")
    fi
  done < <(audit_excludes)
  exclude_args+=("--exclude-dir=.git" "--exclude-dir=node_modules" "--binary-files=without-match")

  local -a declared_paths=()
  while IFS=$'\t' read -r path _field; do
    declared_paths+=("$path")
  done < <(declared_files)

  # Distinguish grep "no matches" (exit 1) from grep FAILURE (exit >1, e.g. a
  # grep that lacks --exclude-dir) — a failed grep must not read as "all clear".
  local grep_out="" grep_status=0
  grep_out=$(grep -rn "${exclude_args[@]}" -F "$current_version" "$REPO_ROOT") || grep_status=$?
  if [[ "$grep_status" -gt 1 ]]; then
    echo "error: grep failed (exit $grep_status) — audit inconclusive" >&2
    return 1
  fi

  local found_undeclared=0
  while IFS= read -r match; do
    [[ -n "$match" ]] || continue
    local match_file rel_path is_declared=0 pfx excluded=0
    match_file=$(echo "$match" | cut -d: -f1)
    rel_path="${match_file#"$REPO_ROOT"/}"
    for pfx in ${exclude_prefixes[@]+"${exclude_prefixes[@]}"}; do
      [[ "$rel_path" == "$pfx"* ]] && { excluded=1; break; }
    done
    [[ "$excluded" -eq 1 ]] && continue
    for dp in "${declared_paths[@]}"; do
      [[ "$rel_path" == "$dp" ]] && { is_declared=1; break; }
    done
    if [[ "$is_declared" -eq 0 ]]; then
      if [[ "$found_undeclared" -eq 0 ]]; then
        echo "UNDECLARED files containing '$current_version':"
        found_undeclared=1
      fi
      echo "  $match"
    fi
  done <<< "$grep_out"

  if [[ "$found_undeclared" -eq 0 ]]; then
    echo "No undeclared files contain the version string. All clear."
  else
    echo ""
    echo "Review the above — bumpable files belong in .version-bump.json's files list,"
    echo "historical/record files (e.g. changelogs) in its audit.exclude list."
  fi

  echo ""
  check_description_drift

  if [[ "$check_status" -ne 0 || "$found_undeclared" -ne 0 ]]; then
    return 1
  fi
}

cmd_bump() {
  local new_version="$1"

  if ! is_valid_version "$new_version"; then
    echo "error: '$new_version' doesn't look like a version (expected X.Y.Z)" >&2
    exit 1
  fi

  validate_config_paths

  # Pre-pass: refuse to start if any declared file is missing (a partial bump
  # leaves the repo with inconsistent versions across manifests).
  local -a missing_files=()
  while IFS=$'\t' read -r path _field; do
    local fullpath="$REPO_ROOT/$path"
    [[ -f "$fullpath" ]] || missing_files+=("$path")
  done < <(declared_files)
  if [[ ${#missing_files[@]} -gt 0 ]]; then
    echo "error: cannot bump — declared file(s) missing:" >&2
    for p in "${missing_files[@]}"; do echo "  $p" >&2; done
    echo "If a write was interrupted mid-loop, restore with git checkout." >&2
    exit 1
  fi

  echo "Bumping all declared files to $new_version..."
  echo ""

  while IFS=$'\t' read -r path field; do
    local fullpath="$REPO_ROOT/$path"
    local old_ver got
    old_ver=$(read_field "$fullpath" "$field")
    write_field "$fullpath" "$new_version"
    # Guard the first-match invariant: verify the write landed on the DECLARED
    # field (a version-like key added earlier in the file would get hit instead).
    got=$(read_field "$fullpath" "$field")
    if [[ "$got" != "$new_version" ]]; then
      echo "error: $path: field '$field' is '$got' after write — the first-match" >&2
      echo "replace hit a different key. Fix the file (or the config) and re-run." >&2
      exit 1
    fi
    printf "  %-50s  %s -> %s\n" "$path ($field)" "$old_ver" "$new_version"
  done < <(declared_files)

  echo ""
  echo "Done. Running audit to check for missed files..."
  echo ""
  cmd_audit
  echo ""
  echo "Remember: add a CHANGELOG.md entry for $new_version (it is deliberately not auto-bumped)."
}

# --- main ---

case "${1:-}" in
  --check)
    cmd_check
    ;;
  --audit)
    cmd_audit
    ;;
  --help|-h|"")
    echo "Usage: scripts/bump-version.sh <new-version> | --check | --audit"
    exit 0
    ;;
  --*)
    echo "error: unknown flag '$1'" >&2
    exit 1
    ;;
  *)
    cmd_bump "$1"
    ;;
esac
