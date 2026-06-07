#!/bin/bash
echo "======================================"
echo "Phase 5 & 6: Seed and InsightFace Test"
echo "======================================"

cd /Users/rudrapratapsinghparmar/Desktop/Attender/attender/backend

echo "1. Running seed.py to validate Database & Models..."
/Users/rudrapratapsinghparmar/miniforge3/bin/python3.12 seed.py

echo ""
echo "2. Running InsightFace validation..."
/Users/rudrapratapsinghparmar/miniforge3/bin/python3.12 test_insightface.py

echo ""
echo "======================================"
echo "Testing Complete. Please paste the output in the chat."
echo "======================================"
