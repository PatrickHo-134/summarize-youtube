#!/bin/bash
set -e

echo "Cleaning up old build artifacts..."
rm -rf package deployment.zip

echo "Creating package directory..."
mkdir -p package

echo "Installing dependencies for Python 3.13 (manylinux2014_x86_64)..."
pip install \
  --platform manylinux2014_x86_64 \
  --target=./package \
  --implementation cp \
  --python-version 3.13 \
  --only-binary=:all: --upgrade \
  youtube-transcript-api openai

echo "Copying lambda function code..."
cp src/lambda_function.py package/

echo "Zipping deployment package..."
cd package
zip -r ../deployment.zip .
cd ..

echo "Build complete: deployment.zip is ready for AWS Lambda upload."