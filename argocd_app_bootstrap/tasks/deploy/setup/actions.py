#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os, copy, shutil

from jinja2 import Environment, FileSystemLoader, environment
from invoke import task, exceptions
from pathlib import Path

from argocd_app_bootstrap.definitions import (
    APP_CONFIG,
    CHILD_REPOS_PATH,
    HELM_BASE_PATH,
    HELM_TEMPLATES_PATH,
    KUSTOMIZED_HELM_PATH,
    OVERLAYS_PATH,
    PATCH_DIR,
    DEPLOY_TEMPLATES_PATH,
    yaml,
)

import argocd_app_bootstrap.tasks.common.actions as common_actions

from argocd_app_bootstrap.utils import common
from argocd_app_bootstrap.utils.common import LOG_ERROR, LOG_INFO, LOG_WARN, publish

## ------------------


@task()
def clone_child_repo(ctxt):
    """
    Clone the project's git repo to data/repo_tmp. This folder is used to stage the ArgoCD
    application and namespace files created by bootstrap_app_of_apps.

    ** This is a helper task and should not be called on its own.
    """

    git_repo = ctxt["child_git_repo"]
    task_desc = "Initializing git + cloning child repo"
    publish(f"START: {task_desc}", LOG_INFO)

    common.clone_repo(ctxt, git_repo, CHILD_REPOS_PATH)

    publish(f"SUCCESS: {task_desc}", LOG_INFO)


## ------------------


@task()
def create_folder_structure(ctxt):
    """
    Create the folder structure for a Kustomized Helm app.

    ** This is a helper task and should not be called on its own.
    """

    task_desc = "Create kustomized helm folder structure"
    publish(f"START: {task_desc}", LOG_INFO)

    try:
        if "argo_proj_yaml" not in ctxt:
            raise Exception("Missing app config")

        Path(KUSTOMIZED_HELM_PATH).mkdir(parents=True, exist_ok=True)
        Path(HELM_BASE_PATH).mkdir(parents=True, exist_ok=True)
        Path(HELM_TEMPLATES_PATH).mkdir(parents=True, exist_ok=True)
        Path(OVERLAYS_PATH).mkdir(parents=True, exist_ok=True)

        for environment in APP_CONFIG["environments"]:
            Path(os.path.join(OVERLAYS_PATH, environment, PATCH_DIR)).mkdir(
                parents=True, exist_ok=True
            )

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e


## ------------------


@task()
def create_template_files(ctxt):
    """
    Create template files for a Kustomized Helm app.

    ** This is a helper task and should not be called on its own.
    """

    task_desc = "Create app of apps folder structure"
    publish(f"START: {task_desc}", LOG_INFO)

    try:
        if "argo_proj_yaml" not in ctxt:
            raise Exception("Missing app config")

        for environment in APP_CONFIG["environments"]:
            shutil.copy2(
                f"{DEPLOY_TEMPLATES_PATH}/deployment_patch.yml.j2",
                f"{OVERLAYS_PATH}/{environment}/{PATCH_DIR}/deployment_patch.yml",
            )

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e


## ------------------


@task()
def render_helm_base_yamls(ctxt):
    """
    Render helm_base folder's Helm templates and kustomization.yml.

    ** This is a helper task and should not be called on its own.
    """

    task_desc = "Create Helm Chart.yaml and deployment YAML templates"
    publish(f"START: {task_desc}", LOG_INFO)

    try:
        if "argo_proj_yaml" not in ctxt:
            raise Exception("Missing app config")

        env = Environment(
            loader=FileSystemLoader(DEPLOY_TEMPLATES_PATH), trim_blocks=True
        )

        # Render Chart.yaml
        rendered_data = env.get_template(f"Chart.yaml.j2").stream(
            app_name=ctxt["child_app_name"],
            app_version=ctxt["argo_proj_yaml"]["argocd"]["parent_app"]["version"],
        )
        rendered_data.dump(f"{HELM_BASE_PATH}/Chart.yaml")

        # Render deployment.yml
        rendered_data = env.get_template(f"deployment.yml.j2").stream()
        rendered_data.dump(f"{HELM_TEMPLATES_PATH}/deployment.yml")

        # Render service.yml
        rendered_data = env.get_template(f"service.yml.j2").stream()
        rendered_data.dump(f"{HELM_TEMPLATES_PATH}/service.yml")

        # Render mapping.yml
        rendered_data = env.get_template(f"mapping.yml.j2").stream(
            app_name=ctxt["child_app_name"]
        )
        rendered_data.dump(f"{HELM_TEMPLATES_PATH}/mapping.yml")

        # Render kustomization_base.yml
        rendered_data = env.get_template(f"kustomization_base.yml.j2").stream(
            app_name=ctxt["child_app_name"],
            parent_app=ctxt["argo_proj_yaml"]["argocd"]["parent_app"]["name"],
            app_version=ctxt["argo_proj_yaml"]["argocd"]["parent_app"]["version"],
        )
        rendered_data.dump(f"{HELM_BASE_PATH}/kustomization.yml")

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e


## ------------------


@task()
def render_overlay_templates_yaml(ctxt):
    """
    Render YAML files in the overlay folders.

    ** This is a helper task and should not be called on its own.
    """

    task_desc = "Create namespace.yaml"
    publish(f"START: {task_desc}", LOG_INFO)

    try:
        if "argo_proj_yaml" not in ctxt:
            raise Exception("Missing app config")

        env = Environment(
            loader=FileSystemLoader(DEPLOY_TEMPLATES_PATH), trim_blocks=True
        )

        for environment in APP_CONFIG["environments"]:
            # Render overlay folder's namespace.yml
            rendered_data = env.get_template(f"namespace.yml.j2").stream(
                namespace=f'{ctxt["child_namespace"]}-{environment}'
            )
            rendered_data.dump(f"{OVERLAYS_PATH}/{environment}/namespace.yml")

            # Render overlay folder's kustomization.yml
            rendered_data = env.get_template(f"kustomization_overlays.yml.j2").stream(
                namespace=f'{ctxt["child_namespace"]}-{environment}'
            )
            rendered_data.dump(f"{OVERLAYS_PATH}/{environment}/kustomization.yml")

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e


## ------------------


@task()
def scaffold_k8s_deployment(ctxt):
    """
    Create scaffolding folder structure for standardized k8s deployments

    ** This is a helper task and should not be called on its own.
    """

    task_desc = "Scaffold"
    publish(f"START: {task_desc}", LOG_INFO)

    try:
        apps_list = ctxt["argo_proj_yaml"]["argocd"]["child_apps"]["app"]
        for app in apps_list:
            common.run_command(ctxt, f"rm -rf {CHILD_REPOS_PATH}")
            ctxt["child_git_repo"] = app["repo_url"]
            ctxt["child_app_name"] = app["name"]
            ctxt["child_namespace"] = app["namespace"]
            publish(f"INFO: Now processing app {ctxt['child_app_name']}", LOG_INFO)

            clone_child_repo(ctxt)
            create_folder_structure(ctxt)
            create_template_files(ctxt)
            render_helm_base_yamls(ctxt)
            render_overlay_templates_yaml(ctxt)
            common_actions.commit_and_push_changes(ctxt),

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e


## ------------------


@task(
    help={
        "git-username": "Git username (optional for some Git providers)",
        "git-token": "Git personal access token",
        "git-repo-url": "Git repo HTTPS URL of the repo where the ArgoCD app definitions are located",
        "argocd-username": "ArgoCD username. Must be a local ArgoCD account (e.g. admin). Does not work with SSO.",
        "argocd-password": "ArgoCD password. Must be a local ArgoCD account. Does not work with SSO.",
    },
    pre=[common_actions.cleanup_data_dir],
    post=[common_actions.clone_repo, scaffold_k8s_deployment],
)
def bootstrap_k8s_deployment(
    ctxt,
    git_username=os.environ.get("GIT_USERNAME"),
    git_token=os.environ.get("GIT_TOKEN"),
    git_repo_url=os.environ.get("GIT_REPO_URL"),
    argocd_username=os.environ.get("ARGOCD_USERNAME"),
    argocd_password=os.environ.get("ARGOCD_PASSWORD"),
):
    """
    Bootstrap an app in ArgoCD using the "App of Apps" pattern. Arguments can be passed
    in through the command line, or they can be set as the following environment variables:

    * GIT_USERNAME
    * GIT_TOKEN
    * GIT_REPO_URL
    * ARGOCD_USERNAME
    * ARGOCD_PASSWORD    
    """
    common.init_bootstrap(
        ctxt,
        git_username,
        git_token,
        git_repo_url,
        argocd_username,
        argocd_password,
        target_repo_path=CHILD_REPOS_PATH,
    )
