#!/bin/bash
# Deploy the translator and app to the current kubectl context (the GKE cluster
# created by infra/milvus-gke), using the images pushed by scripts/build_push.sh.
#
#   PROJECT_ID=my-gcp-project GEMINI_API_KEY=... bash scripts/deploy_gke.sh
#
# Env vars: PROJECT_ID (required), GEMINI_API_KEY (required on first deploy,
#           stored as the k8s secret gemini-api-key), REGION, REPO, TAG
# The k8s/*.yaml files keep the YOUR_PROJECT_ID placeholder; this script renders
# a substituted copy in a temp dir and applies that.
set -euo pipefail
cd "$(dirname "$0")/.."

: "${PROJECT_ID:?set PROJECT_ID to your GCP project id}"
REGION="${REGION:-us-central1}"
REPO="${REPO:-rag-project}"
TAG="${TAG:-v1}"

OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
for f in k8s/app.yaml k8s/translator.yaml; do
  sed -e "s#us-central1-docker.pkg.dev/YOUR_PROJECT_ID/rag-project#${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}#g" \
      -e "s#:v1\$#:${TAG}#" "$f" > "$OUT/$(basename "$f")"
done

if ! kubectl get secret gemini-api-key >/dev/null 2>&1; then
  : "${GEMINI_API_KEY:?set GEMINI_API_KEY to create the gemini-api-key secret}"
  kubectl create secret generic gemini-api-key --from-literal=GEMINI_API_KEY="$GEMINI_API_KEY"
fi

kubectl apply -f k8s/milvus-hpa.yaml
kubectl apply -f "$OUT/translator.yaml"
kubectl apply -f "$OUT/app.yaml"
kubectl rollout status deployment/translator-deployment --timeout=300s
kubectl rollout status deployment/rag-app-deployment --timeout=300s
echo "External IP (may take a minute):"
kubectl get svc rag-app-service
