# Deployment Guide: GCE Instance → Cloud Build → Cloud Run

This guide walks you through deploying the Bilingual Audio Agent to Google Cloud Run
using a GCE (Compute Engine) instance as your build machine for speed.

**Why a GCE instance?** Cloud Build runs on Google's network, so `gcloud builds submit`
uploads your source from the instance at ~10 Gbps instead of your home internet.
Terraform runs faster too since it talks to GCP APIs from inside the same network.

---

## Prerequisites

- GCP project: `x-sorter-489913-c0`
- Your Google AI Studio API key (from .env: `GOOGLE_API_KEY`)
- A GitHub repo with the code pushed

---

## Step 1: Create a GCE Instance

From your local machine or the GCP Console:

```bash
gcloud compute instances create deploy-agent \
  --project=x-sorter-489913-c0 \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB \
  --scopes=cloud-platform
```

The `--scopes=cloud-platform` is critical — it gives the instance permission to call
Cloud Build, Artifact Registry, Cloud Run, and other GCP APIs.

---

## Step 2: SSH into the Instance

```bash
gcloud compute ssh deploy-agent --zone=us-central1-a --project=x-sorter-489913-c0
```

---

## Step 3: Install Tools on the Instance

### 3a. Install Terraform

```bash
sudo apt-get update
sudo apt-get install -y gnupg software-properties-common curl git

# Add HashiCorp GPG key and repo
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list

sudo apt-get update
sudo apt-get install -y terraform
```

Verify:
```bash
terraform --version
```

### 3b. gcloud CLI (already installed on GCE Ubuntu, but verify)

```bash
gcloud --version
```

If not installed (unlikely on GCE):
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

### 3c. Authenticate with Your Google Account

Log in with your own Google account (project owner) — this is the simplest approach
and skips all service account IAM setup:

```bash
gcloud auth login
```

It prints a URL. Open it in your browser, sign in with your Google account,
and paste the authorization code back into the terminal.

Then set the project and authenticate for Terraform:

```bash
gcloud config set project x-sorter-489913-c0
gcloud auth application-default login
```

The second command (`application-default`) is what Terraform uses behind the scenes.
Same flow — URL, browser, paste code.

Since your account is the project owner, you already have all the permissions needed.
No service account IAM bindings required.

---

## Step 4: Clone the Repo

```bash
cd ~
git clone https://github.com/Inflaixus/Gemini-Live-Agent-Challenge-Mar-2026.git
cd Gemini-Live-Agent-Challenge-Mar-2026
git checkout Rag_Agent
```

---

## Step 5: Create terraform.tfvars

```bash
cat > terraform/terraform.tfvars << 'EOF'
project_id     = "x-sorter-489913-c0"
region         = "us-central1"
service_name   = "bilingual-audio-agent"
google_api_key = "YOUR_ACTUAL_API_KEY_HERE"
agent_model    = "gemini-2.5-flash-native-audio-latest"
voice_name     = "Aoede"
EOF
```

**IMPORTANT:** Replace `YOUR_ACTUAL_API_KEY_HERE` with your real API key from `.env`.
Use `nano terraform/terraform.tfvars` to edit it.

---

## Step 6: Enable GCP APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project=x-sorter-489913-c0
```

That's it — since you're logged in as the project owner, no IAM bindings needed.

---

## Step 7: Deploy with Terraform

```bash
cd ~/Gemini-Live-Agent-Challenge-Mar-2026/terraform

# Initialize Terraform (downloads providers)
terraform init

# Preview what will be created
terraform plan

# Deploy everything
terraform apply
```

Type `yes` when prompted.

**What happens:**
1. Terraform enables the required GCP APIs
2. Creates an Artifact Registry Docker repo
3. Runs `gcloud builds submit` to build the Docker image in Cloud Build
4. Deploys the image to Cloud Run with all env vars, WebSocket support, and session affinity
5. Sets IAM policy for public access

This takes about 3-5 minutes on first run.

---

## Step 8: Get Your URL

After `terraform apply` completes:

```bash
terraform output service_url
```

This prints your Cloud Run URL, something like:
```
https://bilingual-audio-agent-xxxxxxxxxx-uc.a.run.app
```

Open it in your browser — you should see the app.

---

## Updating the App (Redeploy)

When you make code changes:

```bash
cd ~/Gemini-Live-Agent-Challenge-Mar-2026

# Pull latest changes
git pull origin Rag_Agent

# Redeploy
cd terraform
terraform apply
```

Terraform detects file changes (app.py, Dockerfile, pyproject.toml) via the hash
trigger and rebuilds the Docker image automatically.

---

## Tear Down (Delete Everything)

```bash
cd ~/Gemini-Live-Agent-Challenge-Mar-2026/terraform
terraform destroy
```

Then delete the GCE instance when you're done:

```bash
# Run this from your LOCAL machine, not the instance
gcloud compute instances delete deploy-agent \
  --zone=us-central1-a \
  --project=x-sorter-489913-c0
```

---

## Troubleshooting

### "Permission denied" on Cloud Build
Make sure you ran Step 6 (IAM bindings). Wait 1-2 minutes after granting roles
for propagation.

### "Deadline exceeded" on terraform apply
Cloud Build can take a few minutes for the first build. If it times out, just
run `terraform apply` again — it will retry the build.

### Cloud Run returns 503
Check logs:
```bash
gcloud run services logs read bilingual-audio-agent \
  --region=us-central1 \
  --project=x-sorter-489913-c0 \
  --limit=50
```

### WebSocket disconnects immediately
Cloud Run has a 60-minute max request timeout. The Terraform config sets
`timeout = "3600s"` (1 hour) which is the max. If sessions drop before that,
it's likely the Gemini Live API's own ~15-min session limit (handled by
session resumption in the code).

### Want to check the Docker image locally on the instance
```bash
cd ~/Gemini-Live-Agent-Challenge-Mar-2026

# Install Docker if needed
sudo apt-get install -y docker.io
sudo usermod -aG docker $USER
newgrp docker

# Build locally to test
docker build -t agent-test .
docker run -p 8080:8080 --env-file .env agent-test
```

---

## Quick Reference (Copy-Paste Cheat Sheet)

```bash
# === ONE-TIME SETUP (on the GCE instance) ===
# Install terraform
sudo apt-get update && sudo apt-get install -y gnupg software-properties-common curl git
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt-get update && sudo apt-get install -y terraform

# Set project
gcloud config set project x-sorter-489913-c0

# Clone
git clone https://github.com/Inflaixus/Gemini-Live-Agent-Challenge-Mar-2026.git
cd Gemini-Live-Agent-Challenge-Mar-2026 && git checkout Rag_Agent

# Create tfvars (edit the API key!)
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
nano terraform/terraform.tfvars

# IAM setup
PROJECT_ID="x-sorter-489913-c0"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com --project=$PROJECT_ID
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" --role="roles/run.admin"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" --role="roles/cloudbuild.builds.editor"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" --role="roles/artifactregistry.admin"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" --role="roles/run.admin"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" --role="roles/iam.serviceAccountUser"

# === DEPLOY ===
cd terraform && terraform init && terraform apply

# === REDEPLOY AFTER CHANGES ===
cd ~/Gemini-Live-Agent-Challenge-Mar-2026 && git pull origin Rag_Agent && cd terraform && terraform apply

# === GET URL ===
terraform output service_url

# === TEAR DOWN ===
terraform destroy
```
