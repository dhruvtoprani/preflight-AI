PYTHONPATH := packages/schemas/src:packages/shared-utils/src:services/orchestrator/src:services/ingestion/src:services/retrieval/src:apps/slack-bot/src:apps/dashboard/src

.PHONY: lint test run-orchestrator run-slack run-dashboard run-local-stack dev-up sync-live check-persistence seed-pilot eval-pilot

lint:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/check_syntax.py

test:
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest discover -s tests -p "test_*.py" -v

run-orchestrator:
	PYTHONPATH=$(PYTHONPATH) uvicorn orchestrator.main:app --reload --port 8000

run-slack:
	PYTHONPATH=$(PYTHONPATH) uvicorn slack_bot.main:app --reload --port 8001

run-dashboard:
	PYTHONPATH=$(PYTHONPATH) uvicorn dashboard_app.main:app --reload --port 8002

run-local-stack:
	bash scripts/run_local_stack.sh

dev-up:
	bash scripts/dev-up.sh

sync-live:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/sync_live_sources.py

check-persistence:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/check_persistence_stack.py

seed-pilot:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/seed_pilot_data.py

eval-pilot:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/run_pilot_eval.py --output .tmp/pilot-eval/report.json $(if $(EVAL_MIN_EVIDENCE_RATIO),--min-evidence-ratio $(EVAL_MIN_EVIDENCE_RATIO),)
