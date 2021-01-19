#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os, copy

from jinja2 import Environment, FileSystemLoader, environment
from invoke import task, exceptions
from pathlib import Path

from argocd_app_bootstrap.definitions import (
    APPS_PARENT_DIR,
    APPS_CHILDREN_DIR,
    APP_CONFIG,
    ARGOCD_DIR,
    DATA_PATH,
    NAMESPACES_PATH,
    PARENT_REPO_PATH,
    ARGOCD_PATH,
    APPS_PARENT_PATH,
    APPS_CHILDREN_PATH,
    TEMPLATES_PATH,
    PROJECTS_PATH,
    ARGO_PROJ_YAML,
    ARGOCD_ROOT,
    yaml,
)

import argocd_app_bootstrap.tasks.common.actions as common_actions
from argocd_app_bootstrap.utils import common
from argocd_app_bootstrap.utils.common import LOG_ERROR, LOG_INFO, LOG_WARN, publish


## ------------------


@task()
def create_folder_structure(ctxt):
    """
    Create the folder structure required by the "App of Apps" pattern.

    ** This is a helper task and should not be called on its own.
    """

    task_desc = "Create app of apps folder structure"
    publish(f"START: {task_desc}", LOG_INFO)

    try:
        if "argo_proj_yaml" not in ctxt:
            raise Exception("Missing app config")

        for environment in APP_CONFIG["environments"]:
            parent_app = ctxt["argo_proj_yaml"]["argocd"]["parent_app"]["name"]
            Path(f"{PROJECTS_PATH}").mkdir(parents=True, exist_ok=True)
            Path(os.path.join(APPS_CHILDREN_PATH, environment)).mkdir(
                parents=True, exist_ok=True
            )

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e


## ------------------


@task()
def create_project_yaml(ctxt):
    """
    Create the project.yml ArgoCD AppProject file associated with this app. Each app will be in its own project.
    
    ** This is a helper task and should not be called on its own.
    """

    task_desc = "Create project.yml"
    publish(f"START: {task_desc}", LOG_INFO)

    try:
        if "argo_proj_yaml" not in ctxt:
            raise Exception("Missing app config")

        for environment in APP_CONFIG["environments"]:
            project_name = (
                f'{ctxt["argo_proj_yaml"]["argocd"]["project"]["name"]}-{environment}'
            )
            project_description = ctxt["argo_proj_yaml"]["argocd"]["project"][
                "description"
            ]

            env = Environment(loader=FileSystemLoader(TEMPLATES_PATH), trim_blocks=True)

            rendered_data = env.get_template(f"project.yml.j2").stream(
                project_name=project_name, project_description=project_description
            )

            rendered_data.dump(f"{PROJECTS_PATH}/project-{environment}.yml")

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e


## ------------------


@task()
def create_root_app_yaml(ctxt):
    """
    Create the root-app.yml ArgoCD Application file definition.

    ** This is a helper task and should not be called on its own.

    """

    environment = ctxt["environment"]
    task_desc = f"Create root-app-{environment}.yml"
    publish(f"START: {task_desc}", LOG_INFO)

    try:
        if "argo_proj_yaml" not in ctxt:
            raise Exception("Missing app config")

        app_of_apps = copy.deepcopy(ctxt["argo_proj_yaml"]["argocd"])

        root_app = {
            "name": f"root-{app_of_apps['parent_app']['name']}",
            "filename": f"root-app-{environment}.yml",
            # "manifest_path": f"{ARGOCD_DIR}/{APPS_PARENT_DIR}/{environment}",
            "manifest_path": f"{ARGOCD_DIR}/{APPS_CHILDREN_DIR}/{environment}",
            "repo_url": app_of_apps["parent_app"]["repo_url"],
        }
        common.process_app_template(
            root_app,
            common.DEFAULT_NAMESPACE,
            common.DESTINATION_CLUSTER_IN_CLUSTER,
            app_of_apps["project"]["name"],
            ARGOCD_PATH,
            environment,
        )

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e


## ------------------


@task()
def create_namespaces_app_yaml(ctxt):
    """
    Create the namespaces-app.yml ArgoCD Application file in the apps-root folder.

    ** This is a helper task and should not be called on its own.
    """

    environment = ctxt["environment"]
    task_desc = f"Create namespaces-{environment}-app.yml"
    publish(f"START: {task_desc}", LOG_INFO)

    try:
        if "argo_proj_yaml" not in ctxt:
            raise Exception("Missing app config")

        app_of_apps = copy.deepcopy(ctxt["argo_proj_yaml"]["argocd"])
        parent_app = {
            "name": f"namespaces-{app_of_apps['parent_app']['name']}",
            "filename": f"namespaces-app-{environment}.yml",
            "manifest_path": f"{ARGOCD_ROOT}/namespaces/{environment}",
            "repo_url": app_of_apps["parent_app"]["repo_url"],
        }
        common.process_app_template(
            parent_app,
            common.DEFAULT_NAMESPACE,
            app_of_apps["child_apps"]["destination_cluster"],
            app_of_apps["project"]["name"],
            os.path.join(APPS_PARENT_PATH, environment),
            environment,
        )

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e


## ------------------


@task()
def create_namespaces_yaml(ctxt):
    """
    Create the namespaces.yml file in the namespaces folder. The namespaces are created
    based on the namespaces listed in the argo_proj.yml file.

    ** This is a helper task and should not be called on its own.
    """

    environment = ctxt["environment"]
    task_desc = f"Create namespaces-{environment}.yml"
    publish(f"START: {task_desc}", LOG_INFO)

    try:
        if "argo_proj_yaml" not in ctxt:
            raise Exception("Missing app config")

        app_of_apps = ctxt["argo_proj_yaml"]["argocd"]
        namespaces = []
        for child_app in app_of_apps["child_apps"]["app"]:
            namespaces.append(f'{child_app["namespace"]}-{environment}')

        env = Environment(loader=FileSystemLoader(TEMPLATES_PATH), trim_blocks=True)
        rendered_data = env.get_template(f"namespaces.yml.j2").stream(
            namespaces=namespaces
        )

        rendered_data.dump(
            f"{NAMESPACES_PATH}/{environment}/namespaces-{environment}.yml"
        )

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e


## ------------------


@task()
def create_parent_apps_yaml(ctxt):
    """
    Create the {app_name}-app.yml ArgoCD Application file defined parent_app.name in the argo_proj.yml file

    ** This is a helper task and should not be called on its own.
    """

    environment = ctxt["environment"]
    task_desc = f"Create {environment} apps-app.yml"
    publish(f"START: {task_desc}", LOG_INFO)

    try:
        if "argo_proj_yaml" not in ctxt:
            raise Exception("Missing app config")

        app_of_apps = copy.deepcopy(ctxt["argo_proj_yaml"]["argocd"])
        parent_app = {
            "name": f'{app_of_apps["parent_app"]["name"]}',
            "manifest_path": f"{ARGOCD_DIR}/{APPS_CHILDREN_DIR}/{environment}",
            "repo_url": app_of_apps["parent_app"]["repo_url"],
        }
        common.process_app_template(
            parent_app,
            common.DEFAULT_NAMESPACE,
            common.DESTINATION_CLUSTER_IN_CLUSTER,
            app_of_apps["project"]["name"],
            os.path.join(APPS_PARENT_PATH, environment),
            environment,
        )

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e


## ------------------


@task()
def create_child_apps_yaml(ctxt):
    """
    Create the *-app.yml ArgoCD Application files related to the target application, defined in the argo_proj.yml file
    These will be created in the apps-{app_name} folder.

    ** This is a helper task and should not be called on its own.
    """

    environment = ctxt["environment"]
    task_desc = f"Create child apps for [{environment}] environment"
    publish(f"START: {task_desc}", LOG_INFO)

    try:
        if "argo_proj_yaml" not in ctxt:
            raise Exception("Missing app config")

        app_of_apps = copy.deepcopy(ctxt["argo_proj_yaml"]["argocd"])
        for child_app in app_of_apps["child_apps"]["app"]:
            child_app["name"] = f"{child_app['name']}"
            child_app["namespace"] = f'{child_app["namespace"]}-{environment}'
            common.process_app_template(
                child_app,
                child_app["namespace"],
                app_of_apps["child_apps"]["destination_cluster"],
                app_of_apps["project"]["name"],
                os.path.join(APPS_CHILDREN_PATH, environment),
                environment,
                deploy_plugin=child_app.get("deploy_plugin", None),
            )

        publish(f"SUCCESS: {task_desc}", LOG_INFO)

    except Exception as e:
        publish(f"FAIL: {task_desc}. CAUSE: {str(e)}", LOG_ERROR)
        raise e


## ------------------


@task()
def create_app_of_apps(ctxt):

    for environment in APP_CONFIG["environments"]:
        ctxt.config["environment"] = environment

        create_root_app_yaml(ctxt)
        # create_namespaces_app_yaml(ctxt)
        # create_namespaces_yaml(ctxt)
        # create_parent_apps_yaml(ctxt)
        create_child_apps_yaml(ctxt)

        ctxt.config["environment"] = "Not Set"


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
    post=[
        common_actions.argocd_login,
        common_actions.clone_repo,
        create_folder_structure,
        create_project_yaml,
        create_app_of_apps,
        common_actions.commit_and_push_changes,
    ],
)
def setup_app_of_apps(
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
        ctxt, git_username, git_token, git_repo_url, argocd_username, argocd_password
    )
