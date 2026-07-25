#!/bin/bash
set -e

echo "Starting Cloudflare Tunnel..."
cloudflared tunnel run --token eyJhIjoiYTE5YzI2NzhkMGExODQ2MGViZjMxZDUzMTEyZDhjM2IiLCJ0IjoiOWQ3NWExNDYtNDhkNi00MmYzLWFmZWEtMDc5ODQ2ZDg2YTdlIiwicyI6Ik5qWXlaR016T0RBdE1ESTVOUzAwWkRRMExXSTNOek10WVRNNU9HRTBPVGt3TkdZMSJ9 &

echo "Starting NEXUS Web Server..."
python main.py --web
