#!/bin/bash
set -euo pipefail

# Configuration
UV="/home/me/.local/bin/uv"
SCRIPT_DIR="/home/me/projects/backup_websites"
CONFIG_FILE="${SCRIPT_DIR}/backup_sites.json"
LOG_FILE="${SCRIPT_DIR}/backup.log"

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
    if [[ ! -f "${CONFIG_FILE}" ]]; then
        echo "Error: Config file not found: ${CONFIG_FILE}"
        exit 1
    fi

    # Create and activate virtual environment if it doesn't exist
    if [[ ! -d ".venv" ]]; then
        echo "Creating virtual environment..."
        ${UV} venv
    fi

    echo "Activating virtual environment..."
    source ".venv/bin/activate"

    # Install package
    echo "Installing backup_websites package..."
    ${UV} pip install -e .
}

# Function to parse and return site configuration
parse_site_config() {
    local site="${1}"
    
    local name=$(echo "${site}" | jq -r '.name')
    local url=$(echo "${site}" | jq -r '.url')
    local download_dir=$(echo "${site}" | jq -r '.download_dir')
    
    echo "${name}|${url}|${download_dir}"
}


# Function to run backup for a single site
run_site_backup() {
    local name="${1}"
    local url="${2}"
    local download_dir="${3}"
    
    echo "Step 1: Running backup for ${name}..."
    
    if ! backup-website --url "${url}" --download-dir "${download_dir}" --log-file "${LOG_FILE}" --name "${name}"; then
        echo "❌ Backup failed for ${name}"
        return 1
    fi
    echo "✅ Backup completed successfully for ${name}"
    return 0
}

# Function to wait for completion marker for a single site
# 
# Waits for the .backup_complete file to be created in the download directory.
# This ensures all subprocesses (like pagination downloads and missing node downloads)
# have finished before proceeding to S3 upload.
wait_for_site_completion() {
    local name="${1}"
    local download_dir="${2}"
    
    python -m backup_websites.wait_for_completion \
        --download-dir "${download_dir}" \
        --name "${name}" \
        --log-file "${LOG_FILE}" \
        --timeout 600 \
        --check-interval 5
}

# Function to upload a single site to S3
upload_site_to_s3() {
    local name="${1}"
    local download_dir="${2}"
    
    echo "Step 3: Uploading ${name} to S3..."
    if python -m backup_websites.s3 "${download_dir}" --s3-folder "${name}" --log-file "${LOG_FILE}"; then
        echo "✅ S3 upload completed successfully for ${name}"
        return 0
    else
        echo "❌ S3 upload failed for ${name}"
        return 1
    fi
}

# Function to run complete pipeline for a single site (backup → wait → S3 upload)
run_site_pipeline() {
    local name="${1}"
    local url="${2}"
    local download_dir="${3}"
    
    echo "=== Starting pipeline for ${name} ==="
    echo "URL: ${url}"
    echo "Download directory: ${download_dir}"
    
    # Create download directory if it doesn't exist
    mkdir -p "${download_dir}"
    
    # Step 1: Run backup
    if ! run_site_backup "${name}" "${url}" "${download_dir}"; then
        echo "❌ Pipeline failed for ${name} - backup step failed"
        return 1
    fi
    
    # Step 2: Wait for completion marker
    if ! wait_for_site_completion "${name}" "${download_dir}"; then
        echo "❌ Pipeline failed for ${name} - completion marker step failed"
        return 1
    fi
    
    # Step 3: Upload to S3
    if ! upload_site_to_s3 "${name}" "${download_dir}"; then
        echo "❌ Pipeline failed for ${name} - S3 upload step failed"
        return 1
    fi
    
    echo "✅ Pipeline completed successfully for ${name}"
    return 0
}


# Function to wait for all pipelines to complete
wait_for_all_pipelines() {
    local -n pids_ref="${1}"
    
    echo "Waiting for all pipelines to complete..."
    local failed=0
    for pid in "${pids_ref[@]}"; do
        wait "${pid}"
        exit_code=$?
        if [[ ${exit_code} -ne 0 ]]; then
            echo "Warning: Pipeline process ${pid} exited with code ${exit_code}"
            failed=1
        fi
    done
    
    if [[ ${failed} -eq 0 ]]; then
        echo "✅ All pipelines completed successfully!"
    else
        echo "⚠ Some pipelines completed with errors"
    fi
}

# Function to run all site pipelines concurrently
run_all_pipelines() {
    local -n pids_ref="${1}"
    
    echo "Reading backup configuration from ${CONFIG_FILE}..."

    # Use process substitution to avoid subshell issue with pipe
    while IFS= read -r site; do
        local site_info=$(parse_site_config "${site}")
        IFS='|' read -r name url download_dir <<< "${site_info}"
        
        # Run complete pipeline in background
        run_site_pipeline "${name}" "${url}" "${download_dir}" &
        
        # Store the PID
        pids_ref+=($!)
        echo "Started pipeline for ${name} (PID: $!)"
        echo
    done < <(jq -c '.sites[]' "${CONFIG_FILE}")
}



main () {
    setup_environment
    
    # Array to store background process PIDs
    local pids=()
    
    # Start all pipelines
    run_all_pipelines pids
    
    # Wait for all pipelines to complete
    wait_for_all_pipelines pids
}

main
