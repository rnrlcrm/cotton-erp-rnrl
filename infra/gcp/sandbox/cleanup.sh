#!/bin/bash
# Cleanup Script for GCP Sandbox
# WARNING: This will DELETE all resources in the sandbox environment

set -e

PROJECT_ID="commodity-plafform-sandbox"
REGION="us-central1"

echo "⚠️  WARNING: This will delete ALL sandbox resources!"
echo "Project: $PROJECT_ID"
echo ""
read -p "Are you sure? (type 'yes' to confirm): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "❌ Cleanup cancelled"
  exit 0
fi

echo "🗑️  Starting cleanup..."

# Set project
gcloud config set project $PROJECT_ID

# Delete Cloud Run services
echo "🔥 Deleting Cloud Run services..."
gcloud run services delete backend-service --region=$REGION --quiet || true
gcloud run services delete frontend-service --region=$REGION --quiet || true
gcloud run jobs delete db-migrate --region=$REGION --quiet || true

# Delete VPC connector
echo "🔥 Deleting VPC connector..."
gcloud compute networks vpc-access connectors delete cotton-erp-connector \
  --region=$REGION --quiet || true

# Delete Cloud SQL instance
echo "🔥 Deleting Cloud SQL instance..."
gcloud sql instances delete cotton-erp-db --quiet || true

# Delete Redis instance
echo "🔥 Deleting Redis instance..."
gcloud redis instances delete cotton-erp-redis --region=$REGION --quiet || true

# Delete storage buckets
echo "🔥 Deleting storage buckets..."
gsutil -m rm -r gs://${PROJECT_ID}-uploads || true
gsutil -m rm -r gs://${PROJECT_ID}-ml-models || true

# Delete Pub/Sub topics and subscriptions
echo "🔥 Deleting Pub/Sub topics..."
for TOPIC in trade-events risk-events payment-events notification-events audit-events; do
  gcloud pubsub subscriptions delete ${TOPIC}-sub --quiet || true
  gcloud pubsub topics delete $TOPIC --quiet || true
done

# Delete secrets
echo "🔥 Deleting secrets..."
for SECRET in database-url redis-url jwt-secret openai-key anthropic-key; do
  gcloud secrets delete $SECRET --quiet || true
done

# Delete service accounts
echo "🔥 Deleting service accounts..."
gcloud iam service-accounts delete backend-runtime@${PROJECT_ID}.iam.gserviceaccount.com --quiet || true

# Delete Artifact Registry repository
echo "🔥 Deleting Artifact Registry..."
gcloud artifacts repositories delete cotton-erp --location=$REGION --quiet || true

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "ℹ️  To delete the entire project:"
echo "  gcloud projects delete $PROJECT_ID"
