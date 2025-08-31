#!/bin/bash
set -euo pipefail

# Add user's local bin to PATH
export PATH="/home/me/.local/bin:${PATH}"

# Script to backup tortillaconsal.com website using wget and upload to S3
# Requires: uv (Python package manager)
# Cron setup: 0 0 1 * * /home/me/projects/backup_websites/tortilla-con-sal-backup.sh

# Full paths to required binaries
UV="/home/me/.local/bin/uv"

# Configuration
EMAIL="eduardolzevallos@gmail.com"
LOG_FILE="/home/me/projects/backup_websites/backup.log"
TEMP_LOG="/tmp/website_backup_$$.log"  # $$ is the PID
exec 1> >(tee -a "${LOG_FILE}")
exec 2>&1

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${1}"
}

error_handler() {
    ERROR_MSG="Error occurred in backup script on line ${1}"
    log "${ERROR_MSG}"
    cat "${TEMP_LOG}" | mail -s "Website Backup Failed - $(date '+%Y-%m-%d')" "${EMAIL}"
    rm -f "${TEMP_LOG}"
    exit 1
}

cleanup() {
    if [ $? -eq 0 ]; then
        log "Backup completed successfully"
        cat "${TEMP_LOG}" | mail -s "Website Backup Successful - $(date '+%Y-%m-%d')" "${EMAIL}"
    fi
    rm -f "${TEMP_LOG}"
}

trap 'error_handler ${LINENO}' ERR
trap cleanup EXIT

# Get the directory where the script is located
SCRIPT_DIR="/home/me/projects/backup_websites"
cd "${SCRIPT_DIR}"

log "Starting backup script"

# Create and activate virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    log "Creating virtual environment..."
    ${UV} venv
fi

# Activate virtual environment
log "Activating virtual environment..."
source .venv/bin/activate

# Install package in development mode
log "Installing package..."
${UV} pip install -e .

# Run the backup script
log "Starting website backup..."
${UV} run backup-website --url "https://tortillaconsal.com/" 

# Cleanup old logs (keep last 5)
find "${SCRIPT_DIR}" -name "backup.log.*" -type f -mtime +30 -delete