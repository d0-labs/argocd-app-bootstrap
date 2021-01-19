#! /bin/bash

# Note: Run this script from the repo root
# Sample usage: ./docker/docker_build.sh <docker_image_tag>

docker_tag=$1

# Get latest versions of our packages
argocd_app_bootstrap_version=$(cat argocd_app_bootstrap/_version.py | grep __version__ | cut -d '=' -f2 | tr -d "\"" | tr -d " ")

echo "argocd_app_bootstrap version: " $argocd_app_bootstrap_version

# Build python code
./build.sh

# Copy wheel files for d0 dependencies
rm docker/*.whl
cp dist/argocd_app_bootstrap-${argocd_app_bootstrap_version}-py3-none-any.whl docker/.

# Copy requirements.txt for external Python dependencies
rm docker/requirements*.txt
cp requirements.txt docker/.

# Copy gcloud credentials file
rm docker/gcloud-sa.json
cp <path_to_keyfile>/<gcloud_sa_keyfile>.json docker/gcloud-sa.json

# Build image
docker build --build-arg ARGOCD_APP_BOOTSTRAP=${argocd_app_bootstrap_version} docker -t argocdapp-bootstrap:${docker_tag}

