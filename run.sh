#!/usr/bin/env bash
# Quick Start Script for Hostel Management Website
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=========================================================="
echo "  🏢 HostelSphere - Hostel Management Website"
echo "  Capstone Project by Jiyansh Sardana (25001003043)"
echo "=========================================================="

# Check Python virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt
fi

# Seed database if not already present
if [ ! -f "hostel.db" ]; then
    echo "Initializing and seeding database..."
    ./venv/bin/python seed_data.py
fi

PORT="${PORT:-5001}"
echo ""
echo "🚀 Starting server at http://127.0.0.1:${PORT}"
echo "----------------------------------------------------------"
echo "  Demo Credentials:"
echo "    👑 Admin / Warden: admin / admin123"
echo "    🎓 Student:        25001003043 / student123"
echo "----------------------------------------------------------"
echo "Press Ctrl+C to stop the server."
echo ""

./venv/bin/python app.py
