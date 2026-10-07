# GKE Deployment Guide - PDF RAG App
**Project:** `YOUR_PROJECT_ID` | **Region:** `us-central1` | **Cluster:** `milvus-gke`

---

## Architecture

```
[Your Browser]
     |
     v
[Streamlit App - LoadBalancer :80]  -->  [Translator - ClusterIP :8080]
     |
     v
[Milvus - LoadBalancer :19530]  (namespace: milvus)
[Attu UI - LoadBalancer :3000]  (namespace: milvus)
```

**Two folders matter:**
- `repo root ` - app code, Dockerfiles, kubectl YAMLs
- `infra/milvus-gke/` - Terraform files for the GKE cluster + Milvus

---

## STEP 1 - Authenticate & Configure gcloud

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud config set compute/region us-central1
gcloud config set compute/zone us-central1-a
```

---

## STEP 2 - Enable Required APIs

```bash
gcloud services enable container.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

---

## STEP 3 - Grant IAM Permissions

Cloud Build requires explicit permissions. Run this once:

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:YOUR_EMAIL@example.com" \
  --role="roles/cloudbuild.builds.editor"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:YOUR_EMAIL@example.com" \
  --role="roles/storage.admin"
```

> Without these, `gcloud builds submit` returns PERMISSION_DENIED.

---

## STEP 4 - Deploy GKE Cluster + Milvus via Terraform

Navigate to the Terraform folder and deploy:

```bash
cd infra/milvus-gke
terraform init
terraform apply -var="project_id=YOUR_PROJECT_ID"
```

Type `yes` when prompted. This takes 5-10 minutes. It creates:
- A GKE cluster named `milvus-gke` with **2 x n2-standard-4 nodes**
- Milvus Standalone (with etcd, MinIO, RocksMQ - no Pulsar)
- Attu web UI
- All exposed via LoadBalancer

> **`variables.tf` change made:** `node_count` was updated from `1` to `2` so Milvus pods
> have enough room to schedule alongside etcd and MinIO.

Once complete, connect kubectl to the cluster:

```bash
gcloud container clusters get-credentials milvus-gke --zone us-central1-a
kubectl get nodes
# Should show 2 nodes with STATUS=Ready
```

Verify Milvus is running:

```bash
kubectl get pods -n milvus
# All pods should show Running
kubectl get svc -n milvus
```

> **Important:** The cluster is named `milvus-gke`, not `rag-cluster`.

---

## STEP 5 - Apply Milvus HPA

The assignment requires the vector database to autoscale (min 1, max 5, CPU >= 70%).
Apply the HPA after Milvus is running:

```bash
cd multilingual-rag-gke   # repo root
kubectl apply -f k8s/milvus-hpa.yaml

# Verify
kubectl get hpa -n milvus
```

---

## STEP 6 - Create Artifact Registry Repository

```bash
gcloud artifacts repositories create rag-project \
  --repository-format docker \
  --location us-central1
```

> If it already exists you will get ALREADY_EXISTS - that is fine, skip ahead.

---

## STEP 7 - Build & Push Images via Cloud Build

> **Do not use `docker push` directly** - Cloud Shell blocks outbound TCP:443 to
> Artifact Registry. Use Cloud Build instead, which builds and pushes entirely
> within Google's infrastructure.

Make sure you are in the correct folder:

```bash
cd multilingual-rag-gke   # repo root
```

### 7a - Translator Image

```bash
cat > /tmp/build-translator.yaml << 'EOF'
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-f', 'Dockerfile.translator', '-t', 'us-central1-docker.pkg.dev/YOUR_PROJECT_ID/rag-project/translator:v1', '.']
images:
- 'us-central1-docker.pkg.dev/YOUR_PROJECT_ID/rag-project/translator:v1'
EOF

gcloud builds submit --config /tmp/build-translator.yaml .
```

Wait for SUCCESS before continuing.

### 7b - App Image

```bash
cat > /tmp/build-app.yaml << 'EOF'
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-f', 'Dockerfile.app', '-t', 'us-central1-docker.pkg.dev/YOUR_PROJECT_ID/rag-project/app:v1', '.']
images:
- 'us-central1-docker.pkg.dev/YOUR_PROJECT_ID/rag-project/app:v1'
EOF

gcloud builds submit --config /tmp/build-app.yaml .
```

Verify both images exist:

```bash
gcloud artifacts docker images list us-central1-docker.pkg.dev/YOUR_PROJECT_ID/rag-project
```

---

## STEP 8 - Add Your Gemini API Key to app.yaml

Store the key as a Kubernetes Secret (`k8s/app.yaml` reads it via `secretKeyRef`, so the key never lands in a tracked file):

```bash
kubectl create secret generic gemini-api-key --from-literal=GEMINI_API_KEY="<your-key>"
```

Also replace `YOUR_PROJECT_ID` in the image paths of `k8s/app.yaml` and `k8s/translator.yaml`.

> `MILVUS_URI` and `TRANSLATOR_URL` are already correct - do not change them.

---

## STEP 9 - Deploy the Translator Service

```bash
cd multilingual-rag-gke   # repo root
kubectl apply -f k8s/translator.yaml

kubectl get pods -l app=translator
kubectl get svc translator-service
# Shows ClusterIP - internal only
```

---

## STEP 10 - Deploy the RAG App + App HPA

```bash
kubectl apply -f k8s/app.yaml

kubectl get pods -l app=rag-app
kubectl get svc rag-app-service
kubectl get hpa rag-app-hpa
```

Wait for the external IP:

```bash
kubectl get svc rag-app-service -w
# Ctrl+C when EXTERNAL-IP shows a real IP
```

---

## STEP 11 - Access the App

```bash
kubectl get svc rag-app-service
```

Open in browser: `http://<EXTERNAL-IP>`

---

## STEP 12 - Verify Each Service Individually

### Translator

```bash
kubectl run test-curl --image=curlimages/curl --restart=Never --rm -it -- \
  curl -X POST http://translator-service.default.svc.cluster.local:8080/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "source_language": "English", "target_language": "Spanish"}'

# Expected: {"translated_text":"Hola Mundo","source_language":"English","target_language":"Spanish"}
```

### Milvus

```bash
kubectl run test-curl --image=curlimages/curl --restart=Never --rm -it -- \
  curl http://milvus.milvus.svc.cluster.local:9091/healthz

# Expected: OK
```

### Logs

```bash
kubectl logs -l app=rag-app --tail=50
kubectl logs -l app=translator --tail=50
```

---

## Quick Reference

```bash
# All pods across namespaces
kubectl get pods -A

# All services and IPs
kubectl get svc -A

# Both HPAs (app HPA + Milvus HPA)
kubectl get hpa -A

# Restart app after code change
kubectl rollout restart deployment/rag-app-deployment

# Restart translator after code change
kubectl rollout restart deployment/translator-deployment

# Live logs
kubectl logs -l app=rag-app -f

# Tear down app + translator only (keeps Milvus running)
kubectl delete -f k8s/app.yaml
kubectl delete -f k8s/translator.yaml

# Tear down everything
cd infra/milvus-gke && terraform destroy
```

---

## Rebuilding and Redeploying After Code Changes

```bash
cd multilingual-rag-gke   # repo root

# Rebuild app
gcloud builds submit --config /tmp/build-app.yaml .
kubectl rollout restart deployment/rag-app-deployment

# Rebuild translator
gcloud builds submit --config /tmp/build-translator.yaml .
kubectl rollout restart deployment/translator-deployment
```

---

## Cost Warning

2 x n2-standard-4 nodes cost ~$0.38/hr combined.
When not in use, always destroy via Terraform:

```bash
cd infra/milvus-gke
terraform destroy
```

To bring back up: `terraform apply`, then re-run Steps 5, 9, 10.
Images remain in Artifact Registry so you do not need to rebuild.
