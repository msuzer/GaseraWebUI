#!/bin/bash

echo "Updating deployed code..."
cd /opt/GaseraWebUI || exit 1

# Pull latest from GitHub
sudo git pull origin main || {
  echo "Git pull failed!"
  exit 1
}

# Optional: install updated dependencies
# e.g., pip install -r requirements.txt

# Restart service (customize this)
echo "Restarting service..."
sudo systemctl restart gasera.service

echo "Update complete."