@echo off
echo Starting Superlive Bot with Hypercorn...
cd superlive_bot
hypercorn main:app --bind 0.0.0.0:8000 --reload
pause
