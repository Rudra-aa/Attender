#!/bin/bash
echo "Starting Attender V3 Backend..."
cd /Users/rudrapratapsinghparmar/Desktop/Attender/attender/backend
/Users/rudrapratapsinghparmar/miniforge3/bin/python3.12 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
