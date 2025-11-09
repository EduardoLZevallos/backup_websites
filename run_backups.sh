#!/bin/bash
set -euo pipefail

# Configuration
UV="/home/me/.local/bin/uv"
SCRIPT_DIR="/home/me/projects/backup_websites"
CONFIG_FILE="${SCRIPT_DIR}/backup_sites.json"

# Function to set up the environment
setup_environment() {
    # Set low CPU priority for this script and its children
    renice -n 20 -p $$ > /dev/null
    
    # Change to script directory
    cd "${SCRIPT_DIR}" || {
        echo "Error: Cannot change to script directory ${SCRIPT_DIR}"
        exit 1
    }

    # Check if config file exists
    if [ ! -f "${CONFIG_FILE}" ]; then
        echo "Error: Config file not found: ${CONFIG_FILE}"
        exit 1
    fi

    # Create and activate virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        ${UV} venv
    fi

    echo "Activating virtual environment..."
    source ".venv/bin/activate"

    # Install package
    echo "Installing backup_websites package..."
    ${UV} pip install -e .
}

# Function to backup a single site
backup_site() {
    local name="$1"
    local url="$2"
    local download_dir="$3"
    
    if backup-website --url "$url" --download-dir "$download_dir"; then
        echo "✅ Backup completed successfully for $name"
    else
        echo "❌ Backup failed for $name"
    fi
}

# Function to parse and return site configuration
parse_site_config() {
    local site="$1"
    
    local name=$(echo "$site" | jq -r '.name')
    local url=$(echo "$site" | jq -r '.url')
    local download_dir=$(echo "$site" | jq -r '.download_dir')
    
    echo "$name|$url|$download_dir"
}

# Function to start backup for a single site
start_site_backup() {
    local name="$1"
    local url="$2"
    local download_dir="$3"
    local -n pids_ref="$4"
    
    echo "=== Starting backup for $name ==="
    echo "URL: $url"
    echo "Download directory: $download_dir"
    
    # Create download directory if it doesn't exist
    mkdir -p "$download_dir"
    
    # Run backup in background
    backup_site "$name" "$url" "$download_dir" &
    
    # Store the PID
    pids_ref+=($!)
    echo "Started backup for $name (PID: $!)"
    echo
}

# Function to wait for all backup processes to complete
wait_for_all_backups() {
    local -n pids_ref="$1"
    
    echo "Waiting for all backups to complete..."
    for pid in "${pids_ref[@]}"; do
        wait "$pid"
    done
    echo "All backups completed!"
}

# Function to run all backups concurrently
run_concurrent_backups() {
    echo "Reading backup configuration from ${CONFIG_FILE}..."
    
    # Array to store background process PIDs
    local pids=()

    jq -c '.sites[]' "${CONFIG_FILE}" | while IFS= read -r site; do
        local site_info=$(parse_site_config "$site")
        IFS='|' read -r name url download_dir <<< "$site_info"
        
        start_site_backup "$name" "$url" "$download_dir" pids
    done

    wait_for_all_backups pids
}

# Function to upload all backup directories to S3
upload_all_to_s3() {
    echo "Starting S3 uploads for all backup directories..."
    
    jq -c '.sites[]' "${CONFIG_FILE}" | while IFS= read -r site; do
        local site_info=$(parse_site_config "$site")
        IFS='|' read -r name url download_dir <<< "$site_info"
        
        echo "Uploading backup for $name from $download_dir..."
        ${UV} run s3.py "$download_dir" --s3-folder "$name"
    done
    
    echo "All S3 uploads completed!"
}

main () {
    setup_environment
    run_concurrent_backups
    # upload_all_to_s3
}

main