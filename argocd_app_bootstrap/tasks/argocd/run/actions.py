#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os

from invoke import task
from invoke.tasks import Task

import argocd_app_bootstrap.tasks.common.actions as common_actions
import argocd_app_bootstrap.tasks.argocd.setup.actions as setup

from argocd_app_bootstrap.definitions import (
    APPS_PARENT_PATH,
    ARGOCD_PATH,
    PROJECTS_PATH,
    ROOT_APP,
    yaml,
)

from argocd_app_bootstrap.utils import common
from argocd_app_bootstrap.utils.common import LOG_ERROR, LOG_INFO, LOG_WARN, publish

## ------------------


@task()
def register_repos(ctxt):
    """
    Register the repos in ArgoCD that are specified in the argo_proj.yml.

    ** This is a helper task and should not be called on its own.
    """

    task_desc = "Registering repos with ArgoCD"
    publish(f"START: {task_desc}", LOG_INFO)

    try:

        if "argo_proj_yaml" not in ctxt:
            raise Exception("Missing app config")

        repos_list = common.get_repos(ctxt)
        git_username = (
            ctxt.config["git_username"]
            if ctxt.config["git_username"] is not None
            else "blah"
        )
        for repo_url in repos_list:
            common.run_command(
                ctxt,
                f"argocd repo add {repo_url} --username {git_username} --password {ctxt.config['git_token']}",
            )

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e


## ------------------


@task()
def apply_and_sync(ctxt):
    """
    Deploy the ArgoCD "App of Apps" manifests to Kubernetes, and sync all related apps.
    
    ** This is a helper task and should not be called on its own.
    """

    environment = ctxt["target_environment"]
    task_desc = f"Creating app of apps in ArgoCD for [{environment}] environment"
    publish(f"START: {task_desc}", LOG_INFO)

    try:

        # Create ArgoCD project
        common.run_command(
            ctxt, f"kubectl apply -f {PROJECTS_PATH}/project-{environment}.yml"
        )

        # Apply and sync master app
        with open(f"{ARGOCD_PATH}/{ROOT_APP}-{environment}.yml", "r") as stream:
            root_app_yaml = yaml.load(stream)
            root_app_name = root_app_yaml["metadata"]["name"]

        common.run_command(
            ctxt, f"kubectl apply -f {ARGOCD_PATH}/{ROOT_APP}-{environment}.yml"
        )
        common.run_command(ctxt, f"argocd app sync {root_app_name}")

        parent_app_name = f'{ctxt["argo_proj_yaml"]["argocd"]["parent_app"]["name"]}-app-{environment}'

        common.run_command(
            ctxt,
            f"argocd app sync -l app.kubernetes.io/instance=root-{parent_app_name}",
        )

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e


## ------------------


@task()
def delete_repos(ctxt):

    task_desc = "Deleting repos"
    publish(f"START: {task_desc}", LOG_INFO)

    try:

        if "argo_proj_yaml" not in ctxt:
            raise Exception("Missing app config")

        repos_list = common.get_repos(ctxt)
        for repo_url in repos_list:
            publish(f"INFO: Removing repo [{repo_url}]", LOG_INFO)
            result = common.run_command(
                ctxt, f"argocd repo rm {repo_url}", raise_exception_on_err=False
            )

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e


## ------------------


@task()
def delete_project(ctxt, target_environment=os.environ.get("TARGET_ENVIRONMENT")):

    environment = ctxt["target_environment"]
    task_desc = "Deleting project"
    publish(f"START: {task_desc}", LOG_INFO)

    try:

        # Apply and sync master app
        with open(f"{PROJECTS_PATH}/project-{environment}.yml", "r") as stream:
            project_yaml = yaml.load(stream)
            project_name = project_yaml["metadata"]["name"]

            common.run_command(ctxt, f"argocd proj delete {project_name}")

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e


## ------------------


@task()
def delete_apps(ctxt):
    """
    Destroy the ArgoCD root-app and all its associated child apps and objects (e.g. namespaces).
    This is a cascade delete.
    
    ** This is a helper task and should not be called on its own.
    """

    environment = ctxt["target_environment"]
    task_desc = f"Deleting [root-app-{environment}]. This will delete all related apps and objects"
    publish(f"START: {task_desc}", LOG_INFO)

    try:

        # Get the app name
        with open(f"{ARGOCD_PATH}/{ROOT_APP}-{environment}.yml", "r") as stream:
            root_app_yaml = yaml.load(stream)
            root_app_name = root_app_yaml["metadata"]["name"]

        common.run_command(ctxt, f"argocd app delete {root_app_name}")
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
        "target-environment": "Target environment to deploy to",
    },
    pre=[common_actions.cleanup_data_dir],
    post=[
        common_actions.clone_repo,
        common_actions.argocd_login,
        register_repos,
        apply_and_sync,
    ],
)
def deploy_app_bundle(
    ctxt,
    git_username=os.environ.get("GIT_USERNAME"),
    git_token=os.environ.get("GIT_TOKEN"),
    git_repo_url=os.environ.get("GIT_REPO_URL"),
    argocd_username=os.environ.get("ARGOCD_USERNAME"),
    argocd_password=os.environ.get("ARGOCD_PASSWORD"),
    target_environment=os.environ.get("TARGET_ENVIRONMENT"),
):
    """
    Deploy the ArgoCD "App of Apps" manifests to Kubernetes, and sync all related apps.

    Arguments can be passed in through the command line, or they can be set as the following environment variables:

    * GIT_USERNAME
    * GIT_TOKEN
    * GIT_REPO_URL
    * ARGOCD_USERNAME
    * ARGOCD_PASSWORD    
    * TARGET_ENVIRONMENT
    """

    common.init_bootstrap(
        ctxt,
        git_username,
        git_token,
        git_repo_url,
        argocd_username,
        argocd_password,
        target_environment=target_environment,
    )


## ------------------


@task(
    help={
        "git-username": "Git username (optional for some Git providers)",
        "git-token": "Git personal access token",
        "git-repo-url": "Git repo HTTPS URL of the repo where the ArgoCD app definitions are located",
        "argocd-username": "ArgoCD username. Must be a local ArgoCD account (e.g. admin). Does not work with SSO.",
        "argocd-password": "ArgoCD password. Must be a local ArgoCD account. Does not work with SSO.",
        "target-environment": "Target environment to deploy to",
    },
    pre=[common_actions.cleanup_data_dir],
    post=[common_actions.clone_repo, common_actions.argocd_login, delete_apps],
)
def remove_app_bundle(
    ctxt,
    git_username=os.environ.get("GIT_USERNAME"),
    git_token=os.environ.get("GIT_TOKEN"),
    git_repo_url=os.environ.get("GIT_REPO_URL"),
    argocd_username=os.environ.get("ARGOCD_USERNAME"),
    argocd_password=os.environ.get("ARGOCD_PASSWORD"),
    target_environment=os.environ.get("TARGET_ENVIRONMENT"),
):
    """
    Remove the ArgoCD root-app and all its associated child apps and objects (e.g. namespaces).
    This is a cascade delete.
    
    Arguments can be passed in through the command line, or they can be set as the following environment variables:

    * GIT_USERNAME
    * GIT_TOKEN
    * GIT_REPO_URL
    * ARGOCD_USERNAME
    * ARGOCD_PASSWORD   
    * TARGET_ENVIRONMENT 
    """

    common.init_bootstrap(
        ctxt,
        git_username,
        git_token,
        git_repo_url,
        argocd_username,
        argocd_password,
        target_environment=target_environment,
    )


## ------------------


@task(
    help={
        "git-username": "Git username (optional for some Git providers)",
        "git-token": "Git personal access token",
        "git-repo-url": "Git repo HTTPS URL of the repo where the ArgoCD app definitions are located",
        "argocd-username": "ArgoCD username. Must be a local ArgoCD account (e.g. admin). Does not work with SSO.",
        "argocd-password": "ArgoCD password. Must be a local ArgoCD account. Does not work with SSO.",
        "target-environment": "Target environment to deploy to",
    },
    pre=[common_actions.cleanup_data_dir],
    post=[common_actions.clone_repo, common_actions.argocd_login, delete_project],
)
def remove_project(
    ctxt,
    git_username=os.environ.get("GIT_USERNAME"),
    git_token=os.environ.get("GIT_TOKEN"),
    git_repo_url=os.environ.get("GIT_REPO_URL"),
    argocd_username=os.environ.get("ARGOCD_USERNAME"),
    argocd_password=os.environ.get("ARGOCD_PASSWORD"),
    target_environment=os.environ.get("TARGET_ENVIRONMENT"),
):
    """
    Remove the specified project from ArgoCD.
    
    Arguments can be passed in through the command line, or they can be set as the following environment variables:

    * GIT_USERNAME
    * GIT_TOKEN
    * GIT_REPO_URL
    * ARGOCD_USERNAME
    * ARGOCD_PASSWORD    
    * TARGET_ENVIRONMENT
    """

    common.init_bootstrap(
        ctxt,
        git_username,
        git_token,
        git_repo_url,
        argocd_username,
        argocd_password,
        target_environment=target_environment,
    )


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
    post=[common_actions.clone_repo, common_actions.argocd_login, delete_repos],
)
def remove_repos(
    ctxt,
    git_username=os.environ.get("GIT_USERNAME"),
    git_token=os.environ.get("GIT_TOKEN"),
    git_repo_url=os.environ.get("GIT_REPO_URL"),
    argocd_username=os.environ.get("ARGOCD_USERNAME"),
    argocd_password=os.environ.get("ARGOCD_PASSWORD"),
):
    """
    Remove repos from ArgoCD that are specified in argo_proj.yml.
    
    Arguments can be passed in through the command line, or they can be set as the following environment variables:

    * GIT_USERNAME
    * GIT_TOKEN
    * GIT_REPO_URL
    * ARGOCD_USERNAME
    * ARGOCD_PASSWORD    
    """

    common.init_bootstrap(
        ctxt, git_username, git_token, git_repo_url, argocd_username, argocd_password
    )
