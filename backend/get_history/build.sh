#!/bin/bash
set -e

echo "Cleaning up old build artifacts..."
rm -rf package deployment.zip

echo "Creating package directory..."
mkdir -p package

echo "Copying lambda function source..."
cp -r src package/src

echo "Zipping deployment package..."
cd package
zip -r ../deployment.zip .
cd ..

rm -rf package

echo "Build complete: deployment.zip is ready for AWS Lambda upload."
