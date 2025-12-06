#!/bin/bash
# GCP Sandbox Setup Script
# Project: commodity-plafform-sandbox
# 
# This script provisions all required GCP infrastructure for the sandbox environment

set -e

PROJECT_ID="commodity-plafform-sandbox"
REGION="us-central1"
ZONE="us-central1-a"

echo "🚀 Starting GCP Sandbox Setup for Cotton ERP"
echo "=============================================="
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Set project
gcloud config set project $PROJECT_ID

# ============================================================================
# STEP 1: Create Artifact Registry Repository
# ============================================================================
echo "📦 Step 1/10: Creating Artifact Registry..."
gcloud artifacts repositories create cotton-erp \
  --repository-format=docker \
  --location=$REGION \
  --description="Cotton ERP Docker images" \
  || echo "Repository already exists, skipping..."

# ============================================================================
# STEP 2: Create Cloud SQL PostgreSQL Instance
# ============================================================================
echo "🗄️  Step 2/10: Creating Cloud SQL PostgreSQL instance..."
gcloud sql instances create cotton-erp-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --network=default \
  --no-assign-ip \
  --database-flags=cloudsql.enable_pgvector=on \
  --backup-start-time=03:00 \
  --retained-backups-count=7 \
  || echo "Cloud SQL instance already exists, skipping..."

# Wait for instance to be ready
echo "⏳ Waiting for Cloud SQL instance to be ready..."
gcloud sql operations wait \
  $(gcloud sql operations list --instance=cotton-erp-db --filter="status=PENDING" --format="value(name)" --limit=1) \
  --timeout=600 \
  || true

# Create database
echo "📊 Creating database..."
gcloud sql databases create commodity_erp \
  --instance=cotton-erp-db \
  || echo "Database already exists, skipping..."

# Create database user
echo "👤 Creating database user..."
DB_PASSWORD=$(openssl rand -base64 32)
gcloud sql users create commodity_user \
  --instance=cotton-erp-db \
  --password="$DB_PASSWORD" \
  || echo "User already exists, skipping..."

# Store database URL in Secret Manager
echo "🔐 Storing database credentials in Secret Manager..."
DB_CONNECTION_NAME=$(gcloud sql instances describe cotton-erp-db --format="value(connectionName)")
DATABASE_URL="postgresql://commodity_user:${DB_PASSWORD}@/${commodity_erp}?host=/cloudsql/${DB_CONNECTION_NAME}"
echo -n "$DATABASE_URL" | gcloud secrets create database-url --data-file=- || \
  echo -n "$DATABASE_URL" | gcloud secrets versions add database-url --data-file=-

# ============================================================================
# STEP 3: Create Memorystore Redis Instance
# ============================================================================
echo "⚡ Step 3/10: Creating Memorystore Redis..."
gcloud redis instances create cotton-erp-redis \
  --size=1 \
  --region=$REGION \
  --tier=basic \
  --redis-version=redis_7_0 \
  || echo "Redis instance already exists, skipping..."

# Wait for Redis to be ready
echo "⏳ Waiting for Redis instance to be ready..."
sleep 30

# Get Redis host and store in Secret Manager
REDIS_HOST=$(gcloud redis instances describe cotton-erp-redis --region=$REGION --format="value(host)")
REDIS_PORT=$(gcloud redis instances describe cotton-erp-redis --region=$REGION --format="value(port)")
REDIS_URL="redis://${REDIS_HOST}:${REDIS_PORT}/0"
echo -n "$REDIS_URL" | gcloud secrets create redis-url --data-file=- || \
  echo -n "$REDIS_URL" | gcloud secrets versions add redis-url --data-file=-

# ============================================================================
# STEP 4: Create VPC Serverless Connector
# ============================================================================
echo "🌐 Step 4/10: Creating VPC Serverless Connector..."
gcloud compute networks vpc-access connectors create cotton-erp-connector \
  --region=$REGION \
  --network=default \
  --range=10.8.0.0/28 \
  --min-instances=2 \
  --max-instances=3 \
  --machine-type=e2-micro \
  || echo "VPC connector already exists, skipping..."

# ============================================================================
# STEP 5: Create Cloud Storage Buckets
# ============================================================================
echo "🪣 Step 5/10: Creating Cloud Storage buckets..."
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://${PROJECT_ID}-uploads || echo "Uploads bucket exists"
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://${PROJECT_ID}-ml-models || echo "ML models bucket exists"

# Enable versioning on uploads bucket
gsutil versioning set on gs://${PROJECT_ID}-uploads

# ============================================================================
# STEP 6: Create Pub/Sub Topics
# ============================================================================
echo "📡 Step 6/10: Creating Pub/Sub topics..."
for TOPIC in trade-events risk-events payment-events notification-events audit-events; do
  gcloud pubsub topics create $TOPIC || echo "Topic $TOPIC already exists"
  gcloud pubsub subscriptions create ${TOPIC}-sub --topic=$TOPIC || echo "Subscription exists"
done

# ============================================================================
# STEP 7: Create Service Accounts
# ============================================================================
echo "🔑 Step 7/10: Creating service accounts..."

# Backend runtime service account
gcloud iam service-accounts create backend-runtime \
  --display-name="Backend Runtime Service Account" \
  || echo "Service account already exists"

# Grant permissions to backend service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:backend-runtime@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:backend-runtime@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:backend-runtime@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/pubsub.subscriber"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:backend-runtime@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:backend-runtime@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# ============================================================================
# STEP 8: Create Secrets
# ============================================================================
echo "🔒 Step 8/10: Creating secrets..."

# JWT Secret
JWT_SECRET=$(openssl rand -base64 32)
echo -n "$JWT_SECRET" | gcloud secrets create jwt-secret --data-file=- || \
  echo -n "$JWT_SECRET" | gcloud secrets versions add jwt-secret --data-file=-

# Create placeholder secrets (you'll update these later)
echo -n "sk-your-openai-key-here" | gcloud secrets create openai-key --data-file=- || true
echo -n "sk-your-anthropic-key-here" | gcloud secrets create anthropic-key --data-file=- || true

echo ""
echo "⚠️  IMPORTANT: Update these secrets with real values:"
echo "  - openai-key (OpenAI API key)"
echo "  - anthropic-key (Anthropic API key)"
echo ""
echo "  Run: echo -n 'YOUR_KEY' | gcloud secrets versions add SECRET_NAME --data-file=-"
echo ""

# ============================================================================
# STEP 9: Create Cloud Run Job for Migrations
# ============================================================================
echo "🏃 Step 9/10: Creating Cloud Run job for database migrations..."
gcloud run jobs create db-migrate \
  --image=us-central1-docker.pkg.dev/$PROJECT_ID/cotton-erp/backend:latest \
  --region=$REGION \
  --command=alembic,upgrade,head \
  --set-secrets=DATABASE_URL=database-url:latest \
  --vpc-connector=cotton-erp-connector \
  --service-account=backend-runtime@${PROJECT_ID}.iam.gserviceaccount.com \
  --max-retries=3 \
  --task-timeout=10m \
  || echo "Migration job already exists, updating..."

# ============================================================================
# STEP 10: Enable Cloud Build Trigger
# ============================================================================
echo "🔨 Step 10/10: Cloud Build setup..."
echo ""
echo "To enable CI/CD from GitHub:"
echo "1. Go to: https://console.cloud.google.com/cloud-build/triggers"
echo "2. Click 'Connect Repository'"
echo "3. Select GitHub and authorize"
echo "4. Select repository: rnrlcrm/cotton-erp-rnrl"
echo "5. Create trigger:"
echo "   - Name: deploy-sandbox"
echo "   - Branch: ^main$"
echo "   - Build configuration: cloudbuild.yaml"
echo ""

# ============================================================================
# SUMMARY
# ============================================================================
echo ""
echo "✅ GCP Sandbox Setup Complete!"
echo "================================"
echo ""
echo "📋 Created Resources:"
echo "  ✓ Artifact Registry: cotton-erp"
echo "  ✓ Cloud SQL: cotton-erp-db (PostgreSQL 15)"
echo "  ✓ Memorystore: cotton-erp-redis (Redis 7)"
echo "  ✓ VPC Connector: cotton-erp-connector"
echo "  ✓ Storage Buckets: uploads, ml-models"
echo "  ✓ Pub/Sub Topics: trade-events, risk-events, etc."
echo "  ✓ Service Accounts: backend-runtime"
echo "  ✓ Secrets: database-url, redis-url, jwt-secret"
echo ""
echo "🔐 Database Connection:"
echo "  Connection Name: $DB_CONNECTION_NAME"
echo "  Database: commodity_erp"
echo "  User: commodity_user"
echo ""
echo "⚡ Redis Connection:"
echo "  Host: $REDIS_HOST"
echo "  Port: $REDIS_PORT"
echo ""
echo "📝 Next Steps:"
echo "  1. Update API keys in Secret Manager (openai-key, anthropic-key)"
echo "  2. Connect GitHub repository to Cloud Build"
echo "  3. Push code to trigger first deployment"
echo "  4. Run: gcloud run services list --region=$REGION"
echo ""
echo "💰 Estimated Monthly Cost: \$60-100"
echo ""
