# NEXUS Honeypot / Canary Files
# ═══════════════════════════════════════════════════════════════════
#
# These files are **intentional decoys** used by the NEXUS ethical hacking
# and OSINT modules to detect unauthorized access attempts.
#
# ⚠️  NONE of these contain real credentials, keys, or wallet data.
#
# They exist so that:
#   1. The OSINT engine can demonstrate credential-hunting behavior
#   2. Security scanners can be tested for false-positive handling
#   3. Intrusion detection canaries trigger alerts on access
#
# Files:
#   .admin_passwords.txt  — Fake admin credentials
#   .bitcoin_wallet.dat   — Fake Bitcoin wallet with Satoshi's genesis address
#   .credentials.json     — Fake AWS API key
#   .env.backup           — Fake environment variables
#   .ssh_keys/id_rsa      — Fake SSH private key (truncated, invalid)
#
# If a security scanner flags these files, that is expected behavior.
# They should NOT be added to .gitignore — their presence is intentional.
