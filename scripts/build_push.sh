#!/bin/bash
# Build the app and translator images and push them to Artifact Registry.
#
#   PROJECT_ID=my-gcp-project bash scripts/build_push.sh            # Cloud Build (default)
#   PROJECT_ID=my-gcp-project bash scripts/build_push.sh --local    # local docker buildx + push
#
# Env vars: PROJECT_ID (required), REGION (default us-central1),
#           REPO (default rag-project), TAG (default v1)
# Cloud Build is the default because Cloud Shell blocks direct docker pushes
# to Artifact Registry (see docs/GKE_DEPLOYMENT_GUIDE.md, step 7).
set -euo pipefail
cd "$(dirname "$0")/.."

: "${PROJECT_ID:?set PROJECT_ID to your GCP project id}"
REGION="${REGION:-us-central1}"
REPO="${REPO:-rag-project}"
TAG="${TAG:-v1}"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}"

gcloud artifacts repositories describe "$REPO" --location "$REGION" --project "$PROJECT_ID" >/dev/null 2>&1 \
  || gcloud artifacts repositories create "$REPO" --repository-format docker \
       --location "$REGION" --project "$PROJECT_ID"

build_one() {  # $1 = image name, $2 = Dockerfile
  local image="${REGISTRY}/$1:${TAG}"
  echo "==> $image ($2)"
  if [ "${MODE}" = "local" ]; then
    docker buildx build --platform linux/amd64 -f "$2" -t "$image" --push .
  else
    local tmp cfg; tmp="$(mktemp -d)"; cfg="$tmp/cloudbuild.yaml"
    cat > "$cfg" <<YAML
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-f', '$2', '-t', '$image', '.']
images:
- '$image'
YAML
    gcloud builds submit --project "$PROJECT_ID" --config "$cfg" .
    rm -rf "$tmp"
  fi
}

MODE="cloud"
[ "${1:-}" = "--local" ] && { MODE="local"; gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet; }

build_one translator Dockerfile.translator
build_one app Dockerfile.app

echo "Pushed: ${REGISTRY}/translator:${TAG} and ${REGISTRY}/app:${TAG}"
