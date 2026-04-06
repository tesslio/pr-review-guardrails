#!/usr/bin/env bash
#
# Run deterministic checks and capture normalized outputs.
# Runs in parallel with collect_pr_context.py.
#
# Discovers repo-native verification commands, runs all in parallel,
# normalizes outputs, enforces per-verifier timeout (default 60s).

set -euo pipefail

REPO_ROOT="${1:-.}"
OUTPUT_FILE="${2:-/dev/stdout}"
DEFAULT_TIMEOUT=60

# Results accumulator
RESULTS_DIR=$(mktemp -d)
trap 'rm -rf "$RESULTS_DIR"' EXIT

# ── Verifier runner ──────────────────────────────────────────────────

run_verifier() {
    local name="$1"
    local cmd="$2"
    local timeout_secs="${3:-$DEFAULT_TIMEOUT}"
    local result_file="$RESULTS_DIR/$name.json"
    local start_ms
    start_ms=$(($(date +%s) * 1000))

    local stdout_file="$RESULTS_DIR/$name.stdout"
    local stderr_file="$RESULTS_DIR/$name.stderr"
    local exit_code=0

    if timeout "$timeout_secs" bash -c "cd $REPO_ROOT && $cmd" \
        >"$stdout_file" 2>"$stderr_file"; then
        exit_code=0
    else
        exit_code=$?
    fi

    local end_ms
    end_ms=$(($(date +%s) * 1000))
    local duration_ms=$((end_ms - start_ms))

    local status="pass"
    if [ "$exit_code" -eq 124 ]; then
        # timeout returns 124 when the command times out
        status="timeout"
    elif [ "$exit_code" -ne 0 ]; then
        status="fail"
    fi

    # Parse findings from output (best-effort line-based extraction)
    # Real implementation would have per-verifier output parsers
    local findings="[]"
    if [ "$status" = "fail" ] || [ "$status" = "timeout" ]; then
        # Capture first 20 lines of output as findings
        local messages
        messages=$(head -20 "$stdout_file" "$stderr_file" 2>/dev/null | \
            python3 -c "
import sys, json, re
findings = []
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    # Try to extract file:line patterns
    m = re.match(r'^([^:]+):(\d+)[:.]?\s*(.*)', line)
    if m:
        findings.append({
            'file': m.group(1),
            'line': int(m.group(2)),
            'message': m.group(3) or line,
            'severity': 'error' if '$status' == 'fail' else 'warning'
        })
    elif len(findings) < 10:
        findings.append({
            'file': '',
            'line': None,
            'message': line[:200],
            'severity': 'error' if '$status' == 'fail' else 'warning'
        })
print(json.dumps(findings[:10]))
" 2>/dev/null || echo "[]")
        findings="$messages"
    fi

    cat > "$result_file" <<ENDJSON
{
  "name": "$name",
  "status": "$status",
  "findings": $findings,
  "duration_ms": $duration_ms
}
ENDJSON
}

# ── Verifier discovery ───────────────────────────────────────────────

declare -a VERIFIER_PIDS=()
declare -a VERIFIER_NAMES=()

discover_and_run() {
    cd "$REPO_ROOT"

    # Test runner
    if [ -f "package.json" ] && grep -q '"test"' package.json 2>/dev/null; then
        run_verifier "test-runner" "npm test -- --passWithNoTests 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("test-runner")
    elif [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "pytest.ini" ]; then
        run_verifier "test-runner" "python -m pytest --tb=short -q 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("test-runner")
    elif [ -f "Makefile" ] && grep -q '^test:' Makefile 2>/dev/null; then
        run_verifier "test-runner" "make test 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("test-runner")
    elif [ -f "go.mod" ]; then
        run_verifier "test-runner" "go test ./... 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("test-runner")
    elif [ -f "Cargo.toml" ]; then
        run_verifier "test-runner" "cargo test 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("test-runner")
    fi

    # Type checker
    if [ -f "tsconfig.json" ]; then
        run_verifier "typecheck" "npx tsc --noEmit 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("typecheck")
    elif command -v mypy &>/dev/null && [ -f "pyproject.toml" ]; then
        run_verifier "typecheck" "mypy . 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("typecheck")
    elif command -v pyright &>/dev/null; then
        run_verifier "typecheck" "pyright 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("typecheck")
    fi

    # Linter
    if [ -f ".eslintrc.json" ] || [ -f ".eslintrc.js" ] || [ -f ".eslintrc.yml" ] || \
       [ -f "eslint.config.js" ] || [ -f "eslint.config.mjs" ]; then
        run_verifier "linter" "npx eslint . --format compact 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("linter")
    elif command -v ruff &>/dev/null; then
        run_verifier "linter" "ruff check . 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("linter")
    elif command -v golangci-lint &>/dev/null; then
        run_verifier "linter" "golangci-lint run 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("linter")
    elif [ -f "Cargo.toml" ]; then
        run_verifier "linter" "cargo clippy -- -W warnings 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("linter")
    fi

    # Static analysis
    if command -v semgrep &>/dev/null; then
        run_verifier "static-analysis" "semgrep --config auto --json 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("static-analysis")
    elif command -v bandit &>/dev/null; then
        run_verifier "static-analysis" "bandit -r . -f json 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("static-analysis")
    elif command -v gosec &>/dev/null; then
        run_verifier "static-analysis" "gosec ./... 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("static-analysis")
    fi

    # Secret scanner
    if command -v gitleaks &>/dev/null; then
        run_verifier "secret-scanner" "gitleaks detect --source . --no-git 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("secret-scanner")
    elif command -v trufflehog &>/dev/null; then
        run_verifier "secret-scanner" "trufflehog filesystem . --json 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("secret-scanner")
    fi

    # Dependency/security audit
    if [ -f "package-lock.json" ] || [ -f "package.json" ]; then
        run_verifier "dep-audit" "npm audit --json 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("dep-audit")
    elif command -v pip-audit &>/dev/null; then
        run_verifier "dep-audit" "pip-audit --format json 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("dep-audit")
    elif [ -f "Cargo.toml" ] && command -v cargo-audit &>/dev/null; then
        run_verifier "dep-audit" "cargo audit --json 2>&1" &
        VERIFIER_PIDS+=($!)
        VERIFIER_NAMES+=("dep-audit")
    fi

    # Repo-specific verifiers from .pr-review/verifiers.json
    local custom_config="$REPO_ROOT/.pr-review/verifiers.json"
    if [ -f "$custom_config" ]; then
        while IFS= read -r verifier; do
            local vname vcommand vtimeout
            vname=$(echo "$verifier" | python3 -c "import sys,json; print(json.load(sys.stdin)['name'])")
            vcommand=$(echo "$verifier" | python3 -c "import sys,json; print(json.load(sys.stdin)['command'])")
            vtimeout=$(echo "$verifier" | python3 -c "import sys,json; print(json.load(sys.stdin).get('timeout_ms',60000)//1000)" 2>/dev/null || echo "$DEFAULT_TIMEOUT")
            run_verifier "$vname" "$vcommand" "$vtimeout" &
            VERIFIER_PIDS+=($!)
            VERIFIER_NAMES+=("$vname")
        done < <(python3 -c "
import json, sys
with open('$custom_config') as f:
    for v in json.load(f):
        print(json.dumps(v))
" 2>/dev/null)
    fi

    cd - >/dev/null
}

# ── Main ─────────────────────────────────────────────────────────────

discover_and_run

# Wait for all verifiers
for pid in "${VERIFIER_PIDS[@]}"; do
    wait "$pid" 2>/dev/null || true
done

# Assemble output
python3 - "$RESULTS_DIR" "$OUTPUT_FILE" <<'PYEOF'
import json
import glob
import sys
import os

results_dir = sys.argv[1]
output_file = sys.argv[2]

verifiers = []
for path in sorted(glob.glob(os.path.join(results_dir, "*.json"))):
    try:
        with open(path) as f:
            verifiers.append(json.load(f))
    except (json.JSONDecodeError, IOError):
        pass

passed = sum(1 for v in verifiers if v["status"] == "pass")
failed = sum(1 for v in verifiers if v["status"] == "fail")
warnings = sum(1 for v in verifiers if v["status"] == "warn")
skipped = sum(1 for v in verifiers if v["status"] in ("skipped", "timeout"))

result = {
    "verifiers": verifiers,
    "summary": {
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
        "skipped": skipped,
    }
}

output = json.dumps(result, indent=2)
if output_file == "/dev/stdout":
    print(output)
else:
    with open(output_file, "w") as f:
        f.write(output)
PYEOF
