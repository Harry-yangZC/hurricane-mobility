.PHONY: all google bts clean install test

install:
	pip install -e .

google: install
	jupyter nbconvert --execute --to notebook --inplace notebooks/01_google_mobility_qc.ipynb
	jupyter nbconvert --execute --to notebook --inplace notebooks/02_google_mobility_eda.ipynb

bts: google
	jupyter nbconvert --execute --to notebook --inplace notebooks/03_external_data_ingest.ipynb
	jupyter nbconvert --execute --to notebook --inplace notebooks/04_bts_event_analysis.ipynb

all: bts

test:
	python -m pytest tests/ -v

clean:
	rm -f data/processed/*.parquet
	rm -rf output/figures/* output/tables/*
