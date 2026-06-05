#!/bin/bash
pkill -f uvicorn
proot-distro login ubuntu --shared-tmp -- bash -c "
  source /root/venv/bin/activate &&
  cd /data/data/com.termux/files/home/dev/github/mine/EU_Funds_and_Grants_AI &&
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
"

