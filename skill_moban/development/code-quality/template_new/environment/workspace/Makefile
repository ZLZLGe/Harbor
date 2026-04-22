.PHONY: quality-gate functional-tests clean

quality-gate:
	PYTHONPATH=/app/workspace python /app/workspace/scripts/run_quality_gate.py

functional-tests:
	PYTHONPATH=/app/workspace pytest -q /app/workspace/quality/test_functional.py

clean:
	rm -rf /app/workspace/out/* /app/workspace/state/*
