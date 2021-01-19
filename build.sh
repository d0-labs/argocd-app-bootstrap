#! /bin/bash

package_name="argocd_app_bootstrap"
app_name="argocd-app-bootstrap"

version=$(cat ${package_name}/_version.py | grep __version__ | cut -d '=' -f2 | tr -d "\"" | tr -d " ")

# Cleanup
rm -rf build
rm -rf dist
rm -rf ${package_name}.egg-info
rm -rf venv/lib/python3.8/site-packages/argocd_app_bootstrap
rm -rf venv/lib/python3.8/site-packages/argocd_app_bootstrap-${version}.dist-info
find . -type d -name __pycache__ -not -path "./venv/*" -exec rm -rf {} \;
pip uninstall -y ${app_name}

# Build package
python setup.py bdist_wheel

# Install package
pip install dist/${package_name}-${version}-py3-none-any.whl
