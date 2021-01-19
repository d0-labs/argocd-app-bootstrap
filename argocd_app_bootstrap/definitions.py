#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from ruamel.yaml import YAML


yaml = YAML()

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Sets default environment to development, unless env is explicityly set
if os.environ.get("ENV") is None:
    os.environ["ENV"] = "development"

# Set default behaviour to grab argo_proj.yml from version control
if os.environ.get("USE_LOCAL_ARGO_PROJ") is None:
    os.environ["USE_LOCAL_ARGO_PROJ"] = "false"

with open(os.path.join(ROOT_DIR, "config.yml"), "r") as stream:
    try:
        configs = yaml.load(stream)
        APP_CONFIG = configs[os.environ.get("ENV")]
    except Exception as error:
        print(error)


TEMPLATES_PATH = os.path.join(ROOT_DIR, "templates")
DEPLOY_TEMPLATES_PATH = os.path.join(TEMPLATES_PATH, "deploy")
DATA_PATH = os.path.join(ROOT_DIR, "data")

# ArgoCD app folder structure
ARGOCD_DIR = "argocd"
NAMESPACES_DIR = "namespaces"
PROJECTS_DIR = "projects"
APPS_PARENT_DIR = "apps-parent"
APPS_CHILDREN_DIR = "apps-children"

PARENT_REPO_PATH = os.path.join(DATA_PATH, "parent_repo")
ARGOCD_PATH = os.path.join(PARENT_REPO_PATH, ARGOCD_DIR)
NAMESPACES_PATH = os.path.join(ARGOCD_PATH, NAMESPACES_DIR)
PROJECTS_PATH = os.path.join(ARGOCD_PATH, PROJECTS_DIR)
APPS_PARENT_PATH = os.path.join(ARGOCD_PATH, APPS_PARENT_DIR)
APPS_CHILDREN_PATH = os.path.join(ARGOCD_PATH, APPS_CHILDREN_DIR)

ROOT_APP = "root-app"
ARGO_PROJ_YAML = "argo_proj.yml"

ARGOCD_ROOT = "argocd"

# App deployment folder structure (Helm + Kustomize)
CHILD_REPOS_PATH = os.path.join(DATA_PATH, "child_repos")
KUSTOMIZED_HELM_PATH = os.path.join(CHILD_REPOS_PATH, "kustomized_helm")
HELM_BASE_PATH = os.path.join(KUSTOMIZED_HELM_PATH, "helm_base")
HELM_TEMPLATES_PATH = os.path.join(HELM_BASE_PATH, "templates")

OVERLAYS_PATH = os.path.join(KUSTOMIZED_HELM_PATH, "overlays")

PATCH_DIR = "patch"
