Handoff usage notes

1) Share handoff/all_teamshare.zip with the team.
2) Read paper/sections/overview_cn.tex first for the process summary.
3) Review paper/main_submission.pdf and paper/ai_appendix.pdf next.
4) Unzip task1_artifacts.zip, task2_artifacts.zip, task3_artifacts.zip to access artifacts.
5) Check each task manifest.json and task_log.jsonl for missing files and metrics context.

Build/repack:
- Run: powershell -NoProfile -ExecutionPolicy Bypass -File handoff/package_teamshare.ps1

Notes:
- Packages exclude .env and key/token files by design.
