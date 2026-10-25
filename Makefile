PY := PYTHONPATH=. .venv/bin/python
DBT := ELIGIBLE_DB=data/eligible.duckdb .venv/bin/dbt
DBT_ARGS := --project-dir transform --profiles-dir transform

SYNTHEA_URL := https://raw.githubusercontent.com/synthetichealth/synthea-sample-data/main/downloads/latest/synthea_sample_data_fhir_latest.zip

.PHONY: synthea-data data omop trials criteria n2c2-eval pytest test all clean

synthea-data:  ## Download the Synthea FHIR sample cohort (one-time)
	mkdir -p data/synthea
	curl -sL -o /tmp/synthea.zip "$(SYNTHEA_URL)"
	unzip -q -o /tmp/synthea.zip -d data/synthea && rm /tmp/synthea.zip
	@echo "synthea bundles: $$(ls data/synthea/*.json | wc -l)"

data:  ## Parse Synthea + generate the messy legacy CSV into raw tables
	$(PY) ingestion/synthea/parse_fhir.py
	$(PY) ingestion/legacy_csv/generate_legacy.py

omop:  ## Build + test the OMOP CDM models with dbt
	$(DBT) seed $(DBT_ARGS)
	$(DBT) run $(DBT_ARGS)
	$(DBT) test $(DBT_ARGS)

trials:  ## Fetch trials + eligibility from ClinicalTrials.gov
	$(PY) ingestion/clinicaltrials/fetch_trials.py --condition "type 2 diabetes" --max 30

criteria:  ## Parse trial eligibility into structured criteria (needs DEEPSEEK_API_KEY)
	$(PY) ingestion/clinicaltrials/parse_criteria.py

n2c2-eval:  ## Run the n2c2 benchmark (needs data/n2c2 + DEEPSEEK_API_KEY)
	$(PY) eval/n2c2/run.py --data data/n2c2/test

pytest:  ## Run the Python unit tests
	$(PY) -m pytest tests/ -q

test: omop pytest  ## Run dbt data tests + Python unit tests

all: data omop trials  ## Full local build (LLM criteria parse run separately)

clean:
	rm -f data/eligible.duckdb
	rm -rf transform/target transform/logs
