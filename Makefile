# Common tasks. Env vars are read from your shell (GEMINI_API_KEY, PROJECT_ID, ...).
PY ?= python3
VENV ?= .venv

.PHONY: help install papers milvus-up milvus-down translator app up down build-push deploy infra

help:            ## list targets
	@grep -E "^[a-z-]+:.*##" Makefile | sed -E "s/:.*## /\t/"

install:         ## create .venv and install Python deps
	$(PY) -m venv $(VENV) && $(VENV)/bin/pip install -r requirements.txt

papers:          ## download the open-access sample corpus into ./papers and validate it
	bash scripts/download_papers.sh && $(VENV)/bin/python scripts/validate_papers.py

milvus-up:       ## start local Milvus Standalone (etcd + MinIO + Milvus) on :19530
	docker compose up -d etcd minio milvus

milvus-down:     ## stop local Milvus (data kept in docker volumes)
	docker compose stop etcd minio milvus

translator:      ## run the translator microservice on :8080
	$(VENV)/bin/uvicorn translator:app --host 127.0.0.1 --port 8080

app:             ## run the Streamlit app on :8501 (needs GEMINI_API_KEY, Milvus, translator)
	$(VENV)/bin/streamlit run app.py

up:              ## whole stack in Docker: Milvus + translator + app on :8501
	docker compose up -d --build

down:            ## stop the Docker stack
	docker compose down

infra:           ## create the GKE cluster + Milvus via Terraform (needs PROJECT_ID)
	cd infra/milvus-gke && terraform init && terraform apply -var="project_id=$(PROJECT_ID)"

build-push:      ## build and push images with Cloud Build (needs PROJECT_ID)
	bash scripts/build_push.sh

deploy:          ## deploy translator + app to the current GKE context (needs PROJECT_ID, GEMINI_API_KEY)
	bash scripts/deploy_gke.sh
