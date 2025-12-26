#!/bin/bash

# Configuration
SOURCE_DIR="/"
DEST_MOUNT="/mnt/nas_ross"
BACKUP_DIR="${DEST_MOUNT}/system_backup"
DATE=$(date +%Y-%m-%d-%H%M%S)
LATEST_LINK="${BACKUP_DIR}/latest"
NEW_BACKUP="${BACKUP_DIR}/backup-${DATE}"
LOG_FILE="/var/log/ross_backup.log"

# Excludes
EXCLUDES=(
    "--exclude=/proc"
    "--exclude=/sys"
    "--exclude=/dev"
    "--exclude=/run"
    "--exclude=/tmp"
    "--exclude=/mnt"
    "--exclude=/media"
    "--exclude=/lost+found"
    "--exclude=/var/log"
    "--exclude=/var/cache/apt/archives"
    "--exclude=/home/*/.cache"
    "--exclude=/swapfile"
)

mkdir -p "${BACKUP_DIR}"

# Check if mount is active
if ! mountpoint -q "${DEST_MOUNT}"; then
    echo "$(date): Error - NAS not mounted at ${DEST_MOUNT}" >> "${LOG_FILE}"
    exit 1
fi

echo "$(date): Starting backup to ${NEW_BACKUP}..." >> "${LOG_FILE}"

# Rsync options explanation:
# -a: archive mode (recursive, preserves permissions, times, groups, owners, devices)
# -A: preserve ACLs
# -X: preserve extended attributes
# -v: verbose
# --delete: delete extraneous files from dest dirs
# --link-dest: hardlink to files in DIR when unchanged

rsync -aAXv --delete "${EXCLUDES[@]}" --link-dest="${LATEST_LINK}" "${SOURCE_DIR}" "${NEW_BACKUP}" >> "${LOG_FILE}" 2>&1

STATUS=$?

if [ $STATUS -eq 0 ]; then
    rm -rf "${LATEST_LINK}"
    ln -s "${NEW_BACKUP}" "${LATEST_LINK}"
    echo "$(date): Backup completed successfully." >> "${LOG_FILE}"
else
    echo "$(date): Backup failed with error code ${STATUS}." >> "${LOG_FILE}"
fi

# Cleanup old backups (optional: keep last 30 days)
# find "${BACKUP_DIR}" -maxdepth 1 -name "backup-*" -type d -mtime +30 -exec rm -rf {} +
