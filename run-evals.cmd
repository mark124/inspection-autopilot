@echo off
cd /d "%~dp0"
echo ============================================================
echo  Grounding eval: 25 recent + 25 dangerous inspections
echo  (about 100 live Qwen calls; SILENT for 3-5 minutes - wait)
echo ============================================================
.venv\Scripts\python -m evals.eval_triage --n 25 --dangerous 25
echo.
echo ============================================================
echo  Sabotage eval: deterministic fault injection (instant)
echo ============================================================
.venv\Scripts\python -m evals.eval_triage --sabotage 25
echo.
echo Done. Leave this window open for the recording.
pause
