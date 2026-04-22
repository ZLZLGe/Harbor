.PHONY: clean build publish

clean:
	rm -f /app/output/warehouse.duckdb /app/output/publish_bundle.json /app/output/publish_receipt.json

build:
	PYTHONPATH=/app/workspace python3 -m marketplace_snapshot.cli build

publish:
	PYTHONPATH=/app/workspace python3 -m marketplace_snapshot.cli publish
