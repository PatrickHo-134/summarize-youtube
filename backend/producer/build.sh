#!/bin/bash
set -e

ENV=${1:-dev}

if [[ "$ENV" != "dev" && "$ENV" != "prod" ]]; then
  echo "Error: argument must be 'dev' or 'prod' (got '$ENV')"
  exit 1
fi

OUTPUT_ZIP="deployment-${ENV}.zip"

echo "Building for environment: $ENV"
echo "Cleaning up old build artifacts..."
rm -rf package "$OUTPUT_ZIP"

echo "Creating package directory..."
mkdir -p package

echo "Copying lambda function source..."
cp -r src package/src

echo "Zipping deployment package..."
cd package
zip -r "../$OUTPUT_ZIP" .
cd ..

rm -rf package

echo "Build complete: $OUTPUT_ZIP is ready for AWS Lambda upload."
