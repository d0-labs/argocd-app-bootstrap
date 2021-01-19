#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os, copy

from jinja2 import Environment, FileSystemLoader, environment
from invoke import task, exceptions
from pathlib import Path

from argocd_app_bootstrap.definitions import (
    APP_CONFIG,
    ARGO_PROJ_YAML,
    DATA_PATH,
    PARENT_REPO_PATH,
    yaml,
)

from argocd_app_bootstrap.utils import common
from argocd_app_bootstrap.utils.common import LOG_ERROR, LOG_INFO, LOG_WARN, publish

## ------------------


@task()
def cleanup_data_dir(ctxt):
    """
    Delete the contents of the data dir.
    
    ** This is a helper task and should not be called on its own.
    """

    task_desc = "Clean up data dir"
    publish(f"START: {task_desc}", LOG_INFO)

    try:
        common.run_command(ctxt, f"rm -rf {DATA_PATH}/*")

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e


## ------------------


@task()
def argocd_login(ctxt):
    """
    Log in to ArgoCD via the argocd CLI.
    
    ** This is a helper task and should not be called on its own.
    """

    task_desc = "Login to ArgoCD"
    publish(f"START: {task_desc}", LOG_INFO)

    try:
        insecure = "--insecure" if APP_CONFIG["argocd"]["insecure"] else ""
        argocd_host = APP_CONFIG["argocd"]["host"]
        argocd_port = APP_CONFIG["argocd"]["port"]
        common.run_command(
            ctxt,
            f"argocd login {argocd_host}:{argocd_port} {insecure} --username {ctxt['argocd_username']} --password {ctxt['argocd_password']}",
        )

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e


## ------------------


@task()
def clone_repo(ctxt):
    """
    Clone the project's git repo to data/repo_tmp. This folder is used to stage the ArgoCD
    application and namespace files created by bootstrap_app_of_apps.

    ** This is a helper task and should not be called on its own.
    """

    task_desc = "Initializing git + cloning parent repo"
    publish(f"START: {task_desc}", LOG_INFO)

    common.clone_repo(ctxt, ctxt["git_repo_url"], PARENT_REPO_PATH)

    # Use argo_proj.yml from the app repo
    argo_proj_yaml_path = os.path.join(PARENT_REPO_PATH, ARGO_PROJ_YAML)
    with open(argo_proj_yaml_path, "r") as stream:
        argo_proj_yaml_dict = yaml.load(stream)
        ctxt.config["argo_proj_yaml"] = common.cleanup_argo_proj_yaml(
            argo_proj_yaml_dict
        )

    # Make sure that argo_proj.yml has the correct repo reference
    with open(argo_proj_yaml_path, "w") as argo_proj_file:
        yaml.dump(ctxt["argo_proj_yaml"].__dict__["_config"], argo_proj_file)

    publish(f"SUCCESS: {task_desc}", LOG_INFO)


## ------------------


@task()
def commit_and_push_changes(ctxt):
    """
    Commit and push the newly-created files to git.

    ** This is a helper task and should not be called on its own.
    """

    task_desc = "Commit and push changes"
    publish(f"START: {task_desc}", LOG_INFO)
    target_repo_path = ctxt["git_repo_path"]

    try:

        common.run_command(ctxt, f"cd {target_repo_path} && git status")
        common.run_command(ctxt, f"cd {target_repo_path} && git add .")
        common.run_command(
            ctxt,
            f"cd {target_repo_path} && git commit -m 'ArgoCD app configs'",
            raise_exception_on_err=False,
        )
        common.run_command(
            ctxt, f"cd {target_repo_path} && git push", raise_exception_on_err=False
        )

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e
