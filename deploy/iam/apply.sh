#!/usr/bin/env bash
# ============================================================================
#  Aegis IAM — apply.sh
# ============================================================================
#  DRY-RUN BY DEFAULT. This script will NEVER execute AWS API calls directly.
#  It only PRINTS the commands an operator would run.
#
#  USAGE:
#    ./apply.sh                    # dry-run (default) — prints commands
#    ./apply.sh --print-only       # alias for dry-run
#    ./apply.sh --help             # this message
#
#  To actually create the role, copy/paste the printed commands after
#  explicit human approval in your target account.
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROLE_NAME="${AEGIS_ROLE_NAME:-AegisReadOnlyAgent}"
POLICY_NAME="${AEGIS_POLICY_NAME:-AegisReadOnlyPolicy}"
ACCOUNT_ID_PLACEHOLDER="YOUR_ACCOUNT_ID"

cat <<'BANNER'
==============================================================================
                       !!  DRY-RUN MODE  !!
 Aegis IAM apply.sh — NEVER RUN AGAINST PROD WITHOUT EXPLICIT APPROVAL.
 This script prints AWS CLI commands. It does NOT execute any API calls.
 Review the printed commands with your security team before running them.
==============================================================================
BANNER

MODE="dry-run"
case "${1:-}" in
  --help|-h)
    sed -n '3,17p' "$0"
    exit 0
    ;;
  --dry-run|--print-only|"")
    MODE="dry-run"
    ;;
  *)
    echo "ERROR: unknown argument '$1'" >&2
    echo "This script supports only --dry-run (default) and --print-only." >&2
    exit 2
    ;;
esac

echo ""
echo "Mode: ${MODE}"
echo "Role name:   ${ROLE_NAME}"
echo "Policy name: ${POLICY_NAME}"
echo ""
echo "# -----------------------------------------------------------------"
echo "# Step 1 — Validate policies statically (REQUIRED before apply)"
echo "# -----------------------------------------------------------------"
echo "python3 ${SCRIPT_DIR}/validator.py --all ${SCRIPT_DIR}"
echo ""
echo "# -----------------------------------------------------------------"
echo "# Step 2 — Create the IAM role from trust policy"
echo "# Replace ${ACCOUNT_ID_PLACEHOLDER} in trust-policy.json before running."
echo "# -----------------------------------------------------------------"
echo "aws iam create-role \\"
echo "  --role-name ${ROLE_NAME} \\"
echo "  --assume-role-policy-document file://${SCRIPT_DIR}/aws/trust-policy.json \\"
echo "  --max-session-duration 3600 \\"
echo "  --description 'Aegis AI agent read-only identity' \\"
echo "  --tags Key=project,Value=aegis Key=purpose,Value=readonly-agent"
echo ""
echo "# -----------------------------------------------------------------"
echo "# Step 3 — Create the managed policy"
echo "# -----------------------------------------------------------------"
echo "aws iam create-policy \\"
echo "  --policy-name ${POLICY_NAME} \\"
echo "  --policy-document file://${SCRIPT_DIR}/aws/readonly-policy.json \\"
echo "  --description 'Aegis read-only policy with explicit mutation deny'"
echo ""
echo "# -----------------------------------------------------------------"
echo "# Step 4 — Attach the policy to the role"
echo "# -----------------------------------------------------------------"
echo "aws iam attach-role-policy \\"
echo "  --role-name ${ROLE_NAME} \\"
echo "  --policy-arn arn:aws:iam::${ACCOUNT_ID_PLACEHOLDER}:policy/${POLICY_NAME}"
echo ""
echo "# -----------------------------------------------------------------"
echo "# Step 5 — Verify with IAM Access Analyzer (recommended)"
echo "# -----------------------------------------------------------------"
echo "aws accessanalyzer validate-policy \\"
echo "  --policy-document file://${SCRIPT_DIR}/aws/readonly-policy.json \\"
echo "  --policy-type IDENTITY_POLICY"
echo ""
echo "# -----------------------------------------------------------------"
echo "# Step 6 — Test assume-role (from caller account, MFA required)"
echo "# -----------------------------------------------------------------"
echo "aws sts assume-role \\"
echo "  --role-arn arn:aws:iam::${ACCOUNT_ID_PLACEHOLDER}:role/${ROLE_NAME} \\"
echo "  --role-session-name aegis-test \\"
echo "  --external-id \"\${AEGIS_EXTERNAL_ID}\" \\"
echo "  --serial-number arn:aws:iam::${ACCOUNT_ID_PLACEHOLDER}:mfa/YOUR_USER \\"
echo "  --token-code \"\${MFA_CODE}\" \\"
echo "  --policy file://${SCRIPT_DIR}/aws/session-policy-example.json"
echo ""
echo "=============================================================="
echo "DRY-RUN COMPLETE — NO API CALLS WERE MADE."
echo "=============================================================="
