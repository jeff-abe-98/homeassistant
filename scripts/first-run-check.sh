#!/usr/bin/env bash
# first-run-check.sh — preflight checklist for the home assistant Pi setup.
#
# Prints PASS/FAIL for each requirement and exits non-zero if anything fails.
#
# Usage (from the repo root):
#   bash scripts/first-run-check.sh
#
# Run as the service user or any user that can read config/ and call systemctl.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SETTINGS="$REPO_ROOT/config/settings.yaml"

PASS=0
FAIL=0

ok()   { echo "  [PASS] $*"; PASS=$((PASS + 1)); }
fail() { echo "  [FAIL] $*"; FAIL=$((FAIL + 1)); }

echo "====================================================="
echo " Home Assistant — First-Run Checklist"
echo " Repo: $REPO_ROOT"
echo "====================================================="
echo ""

# ── 1. HailoRT installed ──────────────────────────────────────────────────────
echo "1. HailoRT"

if command -v hailortcli &>/dev/null; then
    ok "hailortcli found ($(hailortcli --version 2>&1 | head -1))"
else
    fail "hailortcli not found — install with: sudo apt install -y hailo-h10-all"
fi

if hailortcli fw-control identify &>/dev/null 2>&1; then
    ok "AI HAT+ 2 detected on PCIe"
else
    fail "AI HAT+ 2 not detected — check PCIe cable and that dtparam=pciex1_gen=3 is in /boot/firmware/config.txt"
fi

echo ""

# ── 2. No CHANGE_ME placeholders in settings.yaml ────────────────────────────
echo "2. settings.yaml credentials"

if [[ ! -f "$SETTINGS" ]]; then
    fail "config/settings.yaml not found — copy config/settings.yaml.example and fill in values"
else
    # Count lines that still say CHANGE_ME (skip comments)
    CHANGE_ME_LINES=$(grep -v '^\s*#' "$SETTINGS" | grep -c 'CHANGE_ME' || true)
    if [[ "$CHANGE_ME_LINES" -eq 0 ]]; then
        ok "No CHANGE_ME placeholders found"
    else
        # List which keys still need values
        while IFS= read -r line; do
            fail "Placeholder still set: $line"
        done < <(grep -v '^\s*#' "$SETTINGS" | grep 'CHANGE_ME' | sed 's/^\s*//')
    fi

    # Check androidtv.host is not the default placeholder
    if grep -q 'host: 192\.168\.x\.x' "$SETTINGS"; then
        fail "androidtv.host is still 192.168.x.x — set your TV's real IP address"
    else
        ok "androidtv.host is configured"
    fi
fi

echo ""

# ── 3. HailoRT model files present ───────────────────────────────────────────
echo "3. Model files"

if [[ -f "$SETTINGS" ]]; then
    LLM_PATH=$(grep 'llm_model_path:' "$SETTINGS" | awk '{print $2}')
    STT_PATH=$(grep 'stt_model_path:' "$SETTINGS" | awk '{print $2}')
    TTS_PATH=$(grep '^\s*model_path:' "$SETTINGS" | awk '{print $2}')

    for model_path in "$LLM_PATH" "$STT_PATH" "$TTS_PATH"; do
        full_path="$REPO_ROOT/$model_path"
        if [[ -f "$full_path" ]]; then
            ok "Model found: $model_path"
        else
            fail "Model missing: $model_path — see docs/setup-guide.md §5 for download instructions"
        fi
    done
else
    fail "Cannot check model paths — settings.yaml missing"
fi

echo ""

# ── 4. Google OAuth token ─────────────────────────────────────────────────────
echo "4. Google OAuth"

GOOGLE_CREDS="$REPO_ROOT/config/google_credentials.json"
GOOGLE_TOKEN="$REPO_ROOT/config/google_token.json"

if [[ -f "$GOOGLE_CREDS" ]] && ! grep -q 'CHANGE_ME\|YOUR_CLIENT_ID' "$GOOGLE_CREDS"; then
    ok "google_credentials.json present"
else
    fail "config/google_credentials.json missing or contains placeholders — see docs/api-keys-setup.md §3"
fi

if [[ -f "$GOOGLE_TOKEN" ]]; then
    ok "google_token.json present (OAuth already authorised)"
else
    fail "config/google_token.json not found — run the assistant once to complete the Google OAuth flow"
fi

echo ""

# ── 5. Spotify token files ────────────────────────────────────────────────────
echo "5. Spotify"

if [[ -f "$SETTINGS" ]]; then
    OWNER_TOKEN=$(grep 'spotify_token_file:' "$SETTINGS" | awk 'NR==1{print $2}')
    EMILY_TOKEN=$(grep 'spotify_token_file:' "$SETTINGS" | awk 'NR==2{print $2}')

    for token_path in "$OWNER_TOKEN" "$EMILY_TOKEN"; do
        full_path="$REPO_ROOT/$token_path"
        if [[ -f "$full_path" ]]; then
            ok "Spotify token found: $token_path"
        else
            fail "Spotify token missing: $token_path — see docs/api-keys-setup.md §4 to authorise each user"
        fi
    done
else
    fail "Cannot check Spotify tokens — settings.yaml missing"
fi

echo ""

# ── 6. Voice profiles enrolled ────────────────────────────────────────────────
echo "6. Voice profiles"

VOICE_DIR="$REPO_ROOT/config/voice_profiles"
if [[ -d "$VOICE_DIR" ]]; then
    PROFILE_COUNT=$(find "$VOICE_DIR" -name '*.npy' | wc -l)
    if [[ "$PROFILE_COUNT" -ge 2 ]]; then
        ok "$PROFILE_COUNT voice profile(s) found in config/voice_profiles/"
    elif [[ "$PROFILE_COUNT" -eq 1 ]]; then
        fail "Only 1 voice profile found — enroll both Owner and Emily (see docs/setup-guide.md §8)"
    else
        fail "No voice profiles found — run: python -m pi.speaker_id.enroll --name Owner"
    fi
else
    fail "config/voice_profiles/ directory missing — run voice enrollment (docs/setup-guide.md §8)"
fi

echo ""

# ── 7. Systemd units active ───────────────────────────────────────────────────
echo "7. Systemd units"

# Only check if systemctl is available (skip in CI / dev environments)
if ! command -v systemctl &>/dev/null; then
    echo "  [SKIP] systemctl not available (non-Pi environment)"
else
    for unit in homeassistant-pi.service homeassistant-scheduler.timer; do
        state=$(systemctl is-active "$unit" 2>/dev/null || true)
        if [[ "$state" == "active" ]]; then
            ok "$unit is active"
        else
            fail "$unit is $state — run: sudo ./deploy/install-pi-service.sh"
        fi
    done
fi

echo ""

# ── Summary ───────────────────────────────────────────────────────────────────
echo "====================================================="
echo " Results: $PASS passed, $FAIL failed"
echo "====================================================="

if [[ "$FAIL" -gt 0 ]]; then
    echo ""
    echo " Fix the items above, then re-run this script."
    echo " See docs/setup-guide.md and docs/api-keys-setup.md for details."
    exit 1
fi

echo ""
echo " All checks passed — the assistant is ready to run."
echo " Start with: python -m pi.main"
