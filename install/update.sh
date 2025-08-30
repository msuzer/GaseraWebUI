#!/bin/bash

echo "Updating deployed code..."
cd /opt/GaseraWebUI || exit 1

# Forcefully discard any local changes
echo "Resetting local changes..."
sudo git reset --hard

# Pull latest from GitHub
sudo git pull origin main || {
  echo "Git pull failed!"
  exit 1
}

# Make sure all install scripts are executable
echo "🔧 Updating script permissions in /install..."
sudo chmod +x install/*.sh

# Optional: install updated dependencies
# e.g., pip install -r requirements.txt

# Restart service (customize this)
echo "Restarting service..."
sudo systemctl restart gasera.service

echo "Update complete."