#!/bin/bash
set -e
echo "[*] Updating repository..."
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart ufq.service
sudo systemctl status ufq.service --no-pager
