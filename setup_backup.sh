#!/bin/bash

# Configuration based on user input
NAS_HOST="nas"
SHARE_NAME="backup_server" # User said "backup_server야"
MOUNT_POINT="/mnt/nas_ross"
SMB_USER="ismc"
SMB_PASS="Qwerasdf11"
BACKUP_SCRIPT_SRC="./ross_backup.sh"
BACKUP_SCRIPT_DEST="/usr/local/bin/ross_backup.sh"

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root (sudo ./setup_backup.sh)"
  exit 1
fi

echo "--- Installing CIFS Utils ---"
apt-get update && apt-get install -y cifs-utils

echo "--- Configuring Mount Point ---"
mkdir -p "${MOUNT_POINT}"

echo "--- Setting up Credentials ---"
# Safe credentials file
cat > /etc/nas_ross_creds <<EOF
username=${SMB_USER}
password=${SMB_PASS}
EOF
chmod 600 /etc/nas_ross_creds

echo "--- Updating /etc/fstab ---"
# Remove existing specific entry if present to avoid duplicates
sed -i "\|\s${MOUNT_POINT}\s|d" /etc/fstab

# Add new entry
# credentials file is safer than password in fstab
echo "//${NAS_HOST}/${SHARE_NAME} ${MOUNT_POINT} cifs credentials=/etc/nas_ross_creds,iocharset=utf8,vers=3.0,noperm 0 0" >> /etc/fstab

echo "--- Mounting NAS ---"
mount -a
if mountpoint -q "${MOUNT_POINT}"; then
    echo "Success: NAS mounted at ${MOUNT_POINT}"
else
    echo "Error: Failed to mount NAS. Check hostname and network."
    # Attempt ping check
    ping -c 2 "${NAS_HOST}"
fi

echo "--- Installing Backup Script ---"
if [ -f "${BACKUP_SCRIPT_SRC}" ]; then
    cp "${BACKUP_SCRIPT_SRC}" "${BACKUP_SCRIPT_DEST}"
    chmod +x "${BACKUP_SCRIPT_DEST}"
    echo "Backup script installed to ${BACKUP_SCRIPT_DEST}"
else
    echo "Error: ${BACKUP_SCRIPT_SRC} not found in current directory."
    exit 1
fi

echo "--- Scheduling Cron Job ---"
# Format: m h  dom mon dow   command
# Daily at 3:00 AM
echo "0 3 * * * root ${BACKUP_SCRIPT_DEST}" > /etc/cron.d/ross_backup

echo "--- Setup Complete ---"
echo "You can verify the backup now by running: sudo ${BACKUP_SCRIPT_DEST}"
