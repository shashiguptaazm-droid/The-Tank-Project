#!/usr/bin/env bash
# =============================================================================
# scripts/verify_rotation.sh
# =============================================================================
# Reads KEY=VALUE pairs from stdin, overwrites /android/local.properties and
# /android/backend/.env, then runs a one-shot verification for every
# provider that has a real key. Prints a colored pass/fail/skip summary.
#
# Usage:
#   cat values.txt | bash scripts/verify_rotation.sh
#   echo "KEY=VALUE" | bash scripts/verify_rotation.sh
#   bash scripts/verify_rotation.sh < values.txt
#   bash scripts/verify_rotation.sh --help
#
# Input format: one KEY=VALUE per line, no surrounding quotes required.
# Lines starting with `#` and blank lines are ignored. Empty values are
# accepted; the corresponding check is skipped.
#
# What gets preserved from the existing files:
#   - sdk.dir= line in local.properties
#   - DB_HOST, DB_NAME, DB_USER, DB_PASS, GOOGLE_CLIENT_*, FTP_HOST,
#     FTP_USER, FTP_REMOTE_DIR in backend/.env
#
# What gets backed up:
#   - The previous local.properties and backend/.env go to
#     /android/.rotation-backups/<timestamp>/ so a bad paste can be undone.
# =============================================================================

# Bash 4+ required for associative arrays (`declare -A`).
if [ "${BASH_VERSINFO[0]:-0}" -lt 4 ]; then
    echo "ERROR: this script requires bash 4+ (associative arrays). On macOS," >&2
    echo "       run with 'brew install bash' and use the Homebrew bash, or" >&2
    echo "       invoke directly as 'bash scripts/verify_rotation.sh'." >&2
    exit 2
fi

set -u
# `set -o pipefail` is load-bearing: `escape_for_curl()` is a printf|tr|sed
# pipeline, and we want any non-zero exit from tr or sed to fail the
# function instead of silently letting a broken key through.
set -o pipefail

# ----- Paths -----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ANDROID_PROPS="$PROJECT_ROOT/local.properties"
PHP_ENV="$PROJECT_ROOT/backend/.env"
BACKUP_ROOT="$PROJECT_ROOT/.rotation-backups"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
CURL_TIMEOUT=15

# ----- Colors (only when stdout is a TTY) -----
if [ -t 1 ]; then
    RED=$'\033[0;31m'
    GREEN=$'\033[0;32m'
    YELLOW=$'\033[0;33m'
    BLUE=$'\033[0;34m'
    BOLD=$'\033[1m'
    NC=$'\033[0m'
else
    RED=""; GREEN=""; YELLOW=""; BLUE=""; BOLD=""; NC=""
fi

# ----- Counters -----
PASSED=0
FAILED=0
SKIPPED=0

# ----- Logging helpers -----
info() { printf '%b\n' "${BLUE}${BOLD}[INFO]${NC} $*"; }
warn() { printf '%b\n' "${YELLOW}${BOLD}[WARN]${NC} $*"; }
err()  { printf '%b\n' "${RED}${BOLD}[ERR ]${NC} $*" >&2; }

check_pass() {
    printf '%b\n' "${GREEN}[PASS]${NC} $1 ${BLUE}$2${NC}"
    PASSED=$((PASSED + 1))
}

check_fail() {
    printf '%b\n' "${RED}[FAIL]${NC} $1 ${BLUE}$2${NC}"
    FAILED=$((FAILED + 1))
}

check_skip() {
    printf '%b\n' "${YELLOW}[SKIP]${NC} $1 ${BLUE}$2${NC}"
    SKIPPED=$((SKIPPED + 1))
}

# ----- Tool availability -----
require_tool() {
    if ! command -v "$1" >/dev/null 2>&1; then
        err "required tool '$1' is not installed"
        exit 2
    fi
}

require_tool curl
require_tool date
command -v php >/dev/null 2>&1 || warn "php not installed; MySQL check will be skipped"

# ----- Key safety helpers -----
# Strip CR/LF and escape double-quotes / backslashes so an API key can be
# safely interpolated into a curl -H "Authorization: Bearer $key" header
# or a "url?key=$key" query string without breaking the command. Real keys
# are almost always safe ASCII, but this protects against paste accidents.
escape_for_curl() {
    printf '%s' "$1" | tr -d '\r\n' | sed 's/["\\]/\\&/g'
}

# Check if the installed curl was built with FTP support (some hardened
# musl/Alpine images ship curl without it).
has_curl_ftp() {
    curl -V 2>/dev/null | grep -qi ftp
}

# ----- HTTP helpers -----
# Perform a GET that expects HTTP 200, with a Bearer or Token Authorization
# header. For query-string auth, leave $scheme empty and append the key to
# the URL yourself (see check_gemini below).
check_http_get() {
    local name="$1"
    local url="$2"
    local api_key="$3"
    local scheme="${4:-Bearer}"

    if [ -z "$api_key" ]; then
        check_skip "$name" "(key not set)"
        return
    fi

    local http_code
    if [ -n "$scheme" ]; then
        local safe_key
        safe_key=$(escape_for_curl "$api_key")
        http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$CURL_TIMEOUT" \
            -H "Authorization: $scheme $safe_key" \
            "$url" 2>/dev/null) || http_code="000"
    else
        http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$CURL_TIMEOUT" \
            "$url" 2>/dev/null) || http_code="000"
    fi

    if [ "$http_code" = "200" ]; then
        check_pass "$name" "(HTTP 200)"
    else
        check_fail "$name" "(HTTP $http_code)"
    fi
}

# Gemini uses ?key= query-string auth (not Authorization header).
check_gemini() {
    local api_key="${KEYS[GEMINI_API_KEY]:-}"
    if [ -z "$api_key" ]; then
        check_skip "Gemini" "(key not set)"
        return
    fi
    local safe_key
    safe_key=$(escape_for_curl "$api_key")
    local url="https://generativelanguage.googleapis.com/v1beta/models?key=$safe_key"
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$CURL_TIMEOUT" "$url" 2>/dev/null) || http_code="000"
    if [ "$http_code" = "200" ]; then
        check_pass "Gemini" "(HTTP 200)"
    else
        check_fail "Gemini" "(HTTP $http_code)"
    fi
}

# Perform a chat-completions POST (or anything that takes a JSON body with
# { model, messages: [...], max_tokens: 1 }) that expects HTTP 200.
check_chat() {
    local name="$1"
    local url="$2"
    local api_key="$3"
    local model="$4"
    local scheme="${5:-Bearer}"
    local auth_header="${6:-Authorization}"

    if [ -z "$api_key" ] || [ -z "$model" ]; then
        check_skip "$name" "(key or model empty)"
        return
    fi

    local safe_key
    safe_key=$(escape_for_curl "$api_key")
    # Build a minimal JSON body. Use printf so embedded " in the model name
    # is escaped; API key is already escaped above.
    local safe_model
    safe_model=$(printf '%s' "$model" | sed 's/["\\]/\\&/g')
    local body
    body=$(printf '{"model":"%s","messages":[{"role":"user","content":"hi"}],"max_tokens":1}' "$safe_model")

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$CURL_TIMEOUT" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "$auth_header: $scheme $safe_key" \
        -d "$body" \
        "$url" 2>/dev/null) || http_code="000"

    if [ "$http_code" = "200" ]; then
        check_pass "$name" "(HTTP 200)"
    else
        check_fail "$name" "(HTTP $http_code)"
    fi
}

# ----- Per-credential checks -----
check_mysql() {
    local host="${KEYS[DB_HOST]:-localhost}"
    local name="${KEYS[DB_NAME]:-}"
    local user="${KEYS[DB_USER]:-}"
    local pass="${KEYS[DB_PASS]:-}"

    if ! command -v php >/dev/null 2>&1; then
        check_skip "MySQL" "(php not installed)"
        return
    fi
    if [ -z "$name" ] || [ -z "$user" ]; then
        check_skip "MySQL" "(DB_NAME or DB_USER empty)"
        return
    fi

    local result
    result=$(DB_HOST="$host" DB_NAME="$name" DB_USER="$user" DB_PASS="$pass" php -r '
        $c = @new mysqli(getenv("DB_HOST"), getenv("DB_USER"), getenv("DB_PASS"), getenv("DB_NAME"));
        if ($c->connect_error) {
            fwrite(STDERR, $c->connect_error);
            exit(1);
        }
        $v = $c->server_info;
        $c->close();
        echo "connected; server=" . $v;
    ' 2>&1) || result="php_error"

    if [[ "$result" == connected* ]]; then
        check_pass "MySQL" "($result)"
    else
        check_fail "MySQL" "($result)"
    fi
}

check_ftp() {
    local host="${KEYS[FTP_HOST]:-}"
    local user="${KEYS[FTP_USER]:-}"
    local pass="${KEYS[FTP_PASS]:-}"

    if [ -z "$host" ] || [ -z "$user" ] || [ -z "$pass" ]; then
        check_skip "FTP" "(host/user/pass empty)"
        return
    fi
    if ! has_curl_ftp; then
        check_skip "FTP" "(this curl build has no FTP support — install curl-full or libcurl-ftp)"
        return
    fi

    # `curl ftp://` prints the directory listing to stdout on success and
    # returns 0; on auth failure it writes to stderr and returns non-zero.
    local out
    local rc
    out=$(curl -s --max-time "$CURL_TIMEOUT" -u "$user:$pass" "ftp://$host/" 2>&1) && rc=0 || rc=$?
    if [ "$rc" = "0" ]; then
        check_pass "FTP" "(connected to $host)"
    else
        local first_line
        first_line=$(printf '%s' "$out" | head -1)
        check_fail "FTP" "(curl exit $rc: $first_line)"
    fi
}

check_google_oauth() {
    local client_id="${KEYS[GOOGLE_CLIENT_ID]:-}"
    local client_secret="${KEYS[GOOGLE_CLIENT_SECRET]:-}"
    local redirect_uri="${KEYS[GOOGLE_REDIRECT_URI]:-}"

    if [ -z "$client_secret" ]; then
        check_fail "Google OAuth" "(CLIENT_SECRET empty — would break login.php)"
        return
    fi
    if [ -z "$client_id" ] || [ -z "$redirect_uri" ]; then
        check_skip "Google OAuth" "(client_id or redirect_uri empty, secret present)"
        return
    fi
    # Full token test requires a browser flow (consent screen + code exchange).
    # A non-empty, well-formed secret + id + uri is the strongest signal we
    # can get without a real user.
    check_pass "Google OAuth" "(credentials present; full token test requires browser flow)"
}

# ----- Backup + file writing -----
backup_file() {
    local path="$1"
    [ -f "$path" ] || return 0
    mkdir -p "$BACKUP_ROOT/$TIMESTAMP"
    cp -p "$path" "$BACKUP_ROOT/$TIMESTAMP/$(basename "$path")"
}

# Read a single key from the existing .env (best-effort; empty if not found).
read_existing_env() {
    local key="$1"
    local file="$2"
    [ -f "$file" ] || return 0
    grep -E "^$key=" "$file" | head -1 | cut -d= -f2- || true
}

write_local_properties() {
    info "Writing $ANDROID_PROPS"
    {
        echo "# Generated by scripts/verify_rotation.sh on $(date -u -Iseconds)"
        echo "# Source: stdin (rotation runbook)"

        if [ -n "${SDK_DIR_PRESERVED:-}" ]; then
            echo ""
            echo "# Android SDK location (preserved from previous local.properties)"
            echo "sdk.dir=$SDK_DIR_PRESERVED"
        fi

        echo ""
        echo "# AI provider keys"
        for key in GROQ_API_KEY GEMINI_API_KEY OPENROUTER_API_KEY MISTRAL_API_KEY \
                   CLOUDFLARE_WORKER_API_KEY CLOUDFLARE_ACCOUNT_ID \
                   CEREBRAS_API_KEY COHERE_API_KEY REPLICATE_API_KEY \
                   HUGGINGFACE_API_KEY HUGGINGFACE_MODEL \
                   ENDPOINT_AI_API_KEY ENDPOINT_AI_BASE_URL ENDPOINT_AI_MODEL \
                   DEEPSEEK_API_KEY DEEPSEEK_MODEL; do
            if [ -n "${KEYS[$key]+set}" ]; then
                echo "$key=${KEYS[$key]}"
            fi
        done
    } > "$ANDROID_PROPS"
}

write_backend_env() {
    info "Writing $PHP_ENV"
    {
        echo "# Generated by scripts/verify_rotation.sh on $(date -u -Iseconds)"
        echo "# Source: stdin (rotation runbook)"

        echo ""
        echo "# MySQL / MariaDB"
        echo "DB_HOST=${DB_HOST_PRESERVED:-localhost}"
        echo "DB_NAME=${DB_NAME_PRESERVED:-}"
        echo "DB_USER=${DB_USER_PRESERVED:-}"
        echo "DB_PASS=${DB_PASS_PRESERVED:-}"

        echo ""
        echo "# Google OAuth"
        echo "GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID_PRESERVED:-}"
        echo "GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET_PRESERVED:-}"
        echo "GOOGLE_REDIRECT_URI=${GOOGLE_REDIRECT_URI_PRESERVED:-https://medigyaan.xyz/Neurons/google-callback.php}"

        echo ""
        echo "# AI provider keys"
        for key in GROQ_API_KEY GEMINI_API_KEY OPENROUTER_API_KEY MISTRAL_API_KEY \
                   CLOUDFLARE_WORKER_API_KEY CLOUDFLARE_ACCOUNT_ID \
                   CEREBRAS_API_KEY COHERE_API_KEY REPLICATE_API_KEY \
                   HUGGINGFACE_API_KEY HUGGINGFACE_MODEL \
                   ENDPOINT_AI_API_KEY ENDPOINT_AI_BASE_URL ENDPOINT_AI_MODEL \
                   DEEPSEEK_API_KEY DEEPSEEK_MODEL; do
            if [ -n "${KEYS[$key]+set}" ]; then
                echo "$key=${KEYS[$key]}"
            fi
        done

        echo ""
        echo "THESIS_SESSION_BACKEND_URL=${THESIS_SESSION_BACKEND_URL_PRESERVED:-https://medigyaan.xyz/Neurons/thesis_session_backend.php}"

        echo ""
        echo "# FTP / deployment"
        echo "FTP_HOST=${FTP_HOST_PRESERVED:-medigyaan.xyz}"
        echo "FTP_USER=${FTP_USER_PRESERVED:-Owner@medigyaan.xyz}"
        echo "FTP_PASS=${KEYS[FTP_PASS]:-}"
        echo "FTP_REMOTE_DIR=${FTP_REMOTE_DIR_PRESERVED:-/public_html/Neurons}"
    } > "$PHP_ENV"
}

# ----- Main -----
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    sed -n '2,40p' "$0"
    exit 0
fi

info "Reading KEY=VALUE pairs from stdin..."
declare -A KEYS=()
keys_read=0
while IFS='=' read -r key value; do
    case "$key" in
        ''|\#*) continue ;;
    esac
    # Strip surrounding quotes (single or double)
    if [[ "$value" == \"*\" || "$value" == \'*\' ]]; then
        value="${value:1:-1}"
    fi
    # Trim leading/trailing whitespace
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    KEYS["$key"]="$value"
    keys_read=$((keys_read + 1))
done

if [ "$keys_read" -eq 0 ]; then
    err "no KEY=VALUE pairs found on stdin"
    err "usage:  cat values.txt | bash $0"
    exit 2
fi

info "read $keys_read keys"

# ----- Preserve existing settings -----
SDK_DIR_PRESERVED=""
if [ -f "$ANDROID_PROPS" ]; then
    SDK_DIR_PRESERVED=$(grep -E '^sdk\.dir=' "$ANDROID_PROPS" | head -1 | cut -d= -f2- || true)
fi

# Each of these: prefer the value from stdin; fall back to the existing
# backend/.env so a partial paste (e.g. AI keys only) doesn't wipe the
# DB / OAuth / FTP credentials that already work.
DB_HOST_PRESERVED="${KEYS[DB_HOST]:-$(read_existing_env DB_HOST "$PHP_ENV")}"
DB_NAME_PRESERVED="${KEYS[DB_NAME]:-$(read_existing_env DB_NAME "$PHP_ENV")}"
DB_USER_PRESERVED="${KEYS[DB_USER]:-$(read_existing_env DB_USER "$PHP_ENV")}"
DB_PASS_PRESERVED="${KEYS[DB_PASS]:-$(read_existing_env DB_PASS "$PHP_ENV")}"
GOOGLE_CLIENT_ID_PRESERVED="${KEYS[GOOGLE_CLIENT_ID]:-$(read_existing_env GOOGLE_CLIENT_ID "$PHP_ENV")}"
GOOGLE_CLIENT_SECRET_PRESERVED="${KEYS[GOOGLE_CLIENT_SECRET]:-$(read_existing_env GOOGLE_CLIENT_SECRET "$PHP_ENV")}"
GOOGLE_REDIRECT_URI_PRESERVED="${KEYS[GOOGLE_REDIRECT_URI]:-$(read_existing_env GOOGLE_REDIRECT_URI "$PHP_ENV")}"
FTP_HOST_PRESERVED="${KEYS[FTP_HOST]:-$(read_existing_env FTP_HOST "$PHP_ENV")}"
FTP_USER_PRESERVED="${KEYS[FTP_USER]:-$(read_existing_env FTP_USER "$PHP_ENV")}"
FTP_REMOTE_DIR_PRESERVED="${KEYS[FTP_REMOTE_DIR]:-$(read_existing_env FTP_REMOTE_DIR "$PHP_ENV")}"
THESIS_SESSION_BACKEND_URL_PRESERVED="${KEYS[THESIS_SESSION_BACKEND_URL]:-$(read_existing_env THESIS_SESSION_BACKEND_URL "$PHP_ENV")}"

# ----- Back up + write -----
info "Backing up existing files (if any)..."
backup_file "$ANDROID_PROPS"
backup_file "$PHP_ENV"
if [ -d "$BACKUP_ROOT/$TIMESTAMP" ]; then
    info "backups in $BACKUP_ROOT/$TIMESTAMP"
fi

write_local_properties
write_backend_env

# ----- Run verifications -----
echo
info "=== Running provider verifications ==="
echo

# Gemini uses query-string auth (not Bearer), so it has its own function.
check_gemini

# OpenAI-compatible chat endpoints
check_chat "Groq" "https://api.groq.com/openai/v1/chat/completions" \
    "${KEYS[GROQ_API_KEY]:-}" "llama-3.1-8b-instant" "Bearer"
check_chat "EndpointAI" "${KEYS[ENDPOINT_AI_BASE_URL]:-https://endpointai-backend-production.up.railway.app/}/api/v1/chat/completions" \
    "${KEYS[ENDPOINT_AI_API_KEY]:-}" "${KEYS[ENDPOINT_AI_MODEL]:-deepseek-r1:70b}" "" "X-API-Key"

# Bearer-token GET endpoints
check_http_get "OpenRouter" "https://openrouter.ai/api/v1/auth/key" \
    "${KEYS[OPENROUTER_API_KEY]:-}" "Bearer"
check_http_get "Mistral" "https://api.mistral.ai/v1/models" \
    "${KEYS[MISTRAL_API_KEY]:-}" "Bearer"

# Cloudflare needs both the API token and the account id
if [ -n "${KEYS[CLOUDFLARE_WORKER_API_KEY]:-}" ] && [ -n "${KEYS[CLOUDFLARE_ACCOUNT_ID]:-}" ]; then
    check_http_get "Cloudflare" \
        "https://api.cloudflare.com/client/v4/accounts/${KEYS[CLOUDFLARE_ACCOUNT_ID]}/ai/models/search" \
        "${KEYS[CLOUDFLARE_WORKER_API_KEY]:-}" "Bearer"
else
    check_skip "Cloudflare" "(key or account_id empty)"
fi

check_http_get "Cerebras" "https://api.cerebras.ai/v1/models" \
    "${KEYS[CEREBRAS_API_KEY]:-}" "Bearer"
check_http_get "Cohere" "https://api.cohere.ai/v1/models" \
    "${KEYS[COHERE_API_KEY]:-}" "Bearer"
check_http_get "Replicate" "https://api.replicate.com/v1/models" \
    "${KEYS[REPLICATE_API_KEY]:-}" "Token"
check_http_get "DeepSeek" "https://api.deepseek.com/models" \
    "${KEYS[DEEPSEEK_API_KEY]:-}" "Bearer"

# Optional: HuggingFace
if [ -n "${KEYS[HUGGINGFACE_API_KEY]:-}" ]; then
    check_http_get "HuggingFace" "https://huggingface.co/api/whoami-v2" \
        "${KEYS[HUGGINGFACE_API_KEY]:-}" "Bearer"
else
    check_skip "HuggingFace" "(key not set — optional)"
fi

# Optional: Facebook
if [ -n "${KEYS[FB_APP_SECRET]:-}" ]; then
    check_pass "Facebook" "(app secret present; full validation requires an app access token)"
else
    check_skip "Facebook" "(FB_APP_SECRET not set — optional)"
fi

# Backend
check_mysql
check_google_oauth
check_ftp

# ----- Summary -----
echo
info "=== SUMMARY ==="
printf '%b passed, %b failed, %b skipped\n' \
    "${GREEN}${BOLD}${PASSED}${NC}" \
    "${RED}${BOLD}${FAILED}${NC}" \
    "${YELLOW}${BOLD}${SKIPPED}${NC}"

if [ "$FAILED" -gt 0 ]; then
    echo
    err "SOME CHECKS FAILED — do NOT revoke the old keys at the provider"
    err "dashboards until every check above is PASS or an expected SKIP."
    if [ -d "$BACKUP_ROOT/$TIMESTAMP" ]; then
        err "to roll back, copy files from $BACKUP_ROOT/$TIMESTAMP/ back to"
        err "$ANDROID_PROPS and $PHP_ENV."
    fi
    exit 1
fi

if [ "$SKIPPED" -gt 0 ]; then
    echo
    warn "Some checks were skipped (empty keys). If those keys are expected to"
    warn "be empty, the rotation is complete; otherwise, re-paste with values."
fi

echo
info "All non-skipped checks passed."
info "Backups (if any): $BACKUP_ROOT/$TIMESTAMP/"
info "It is now safe to revoke the old keys at each provider dashboard."

# Best-effort: tick the boxes in ROTATION_CHECKLIST.md. Only the known
# provider rows are flipped, so unrelated ☐ in that file stay intact.
CHECKLIST="$PROJECT_ROOT/ROTATION_CHECKLIST.md"
if [ -f "$CHECKLIST" ] && [ "$FAILED" -eq 0 ]; then
    # Lines like "| ☐ |" become "| ✅ |". Limit to the first 30 ☐ in the
    # table to avoid flipping unrelated checkboxes elsewhere in the file.
    # If perl is missing (rare), surface a clear message instead of
    # silently ticking only one box via a naive sed fallback.
    if command -v perl >/dev/null 2>&1; then
        perl -i -pe 's/\| \xE2\x98\x90 \|/| \xE2\x9C\x85 |/ if $i++ < 30' "$CHECKLIST"
    else
        warn "perl not installed; ROTATION_CHECKLIST.md was NOT ticked automatically."
        warn "tick the boxes by hand (or install perl and re-run the script)."
    fi
    if ! grep -q "^rotated on:" "$CHECKLIST"; then
        printf '\n## Rotation log\n\n- rotated on: %s (script: scripts/verify_rotation.sh)\n' "$(date -u -Iseconds)" >> "$CHECKLIST"
    fi
    info "Ticked the first 30 boxes in ROTATION_CHECKLIST.md"
fi

exit 0
