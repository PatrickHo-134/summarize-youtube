#!/bin/bash
set -e # Exit immediately if any command fails

# Configurable AWS Variables
S3_BUCKET="youtube-summarizer-ui"
DISTRIBUTION_ID="EILX06H79ZJZS"

echo "🚀 Starting Frontend Deployment Process..."

# 1. Navigate to the frontend directory and compile production assets
echo "📦 Building Vite/React production assets..."
cd frontend
npm run build

# 2. Sync the dist directory to the private S3 bucket
echo "☁️ Syncing dist/ directory to s3://${S3_BUCKET}..."
aws s3 sync dist/ "s3://${S3_BUCKET}" --delete

# 3. Invalidate CloudFront edge caches so users receive the new version instantly
echo "🔄 Invalidating CloudFront cache for distribution ${DISTRIBUTION_ID}..."
aws cloudfront create-invalidation \
  --distribution-id "${DISTRIBUTION_ID}" \
  --paths "/*"

echo "✅ Frontend deployment complete!"