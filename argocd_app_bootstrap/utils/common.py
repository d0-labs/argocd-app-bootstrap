import os, inspect, re, string

from invoke import Context
from jinja2 import Environment, FileSystemLoader
from structlog import get_logger


from argocd_app_bootstrap.definitions import (
    APP_CONFIG,
    ARGO_PROJ_YAML,
    PARENT_REPO_PATH,
    TEMPLATES_PATH,
    yaml,
)

## ------------------


def str2bool(value: str):
    """
    Converts a string to a python bool

    Args:
        value (str): Value to convert

    Returns:
        [type]: [description]
    """
    if type(value) == bool:
        return_val = value
    else:
        return_val = value.lower() in ("yes", "true", "t", "1")

    return return_val


## ------------------

logger = get_logger()

# Logging states
LOG_INFO = "INFO"
LOG_WARN = "WARN"
LOG_ERROR = "ERROR"

DEFAULT_NAMESPACE = "default"
DESTINATION_CLUSTER_IN_CLUSTER = "in-cluster"

## ------------------


def run_command(ctxt: Context, command: str, raise_exception_on_err=True, hide=None):
    """
    Run command-line command

    Args:
        ctxt (Context): PyInvoke Context. http://docs.pyinvoke.org/en/stable/api/context.html
        command (str): The command to execute
        raise_exception_on_err (bool, optional): If false, don't raise an exception. We can use this to capture the error message. Defaults to True.
        hide (bool, optional): If true, hide the command outputs. Valid values: "err", "out", "both", "none". Defaults to None.

    Raises:
        Exception: Exception raised if command errs out (non-zero return code).

    Returns:
        Result: PyInvoke result object. http://docs.pyinvoke.org/en/stable/api/runners.html
    """

    result = ctxt.run(command, warn=True, hide=hide)

    if raise_exception_on_err and (result.exited != 0):
        raise Exception(f"{result.stderr}")

    return result


## ------------------


def publish(msg: str, type: str):
    """
    Wrapper for logging. Future state: post message to listener endpoint (future state)

    Args:
        msg (str): The message to be published.
        type (str): The log type. Valid values: LOG_ERROR, LOG_INFO, LOG_WARN
    """

    # Always include these in every log
    log = logger.bind(
        app="argocd_app_bootstrap", caller=inspect.currentframe().f_back.f_code.co_name
    )

    # Loggers for different occasions
    if type.upper() == LOG_INFO:
        log.info(msg)

    if type.upper() == LOG_ERROR:
        log.error(f"AN ERROR HAS OCCURRED: {msg}")

    if type.upper() == LOG_WARN:
        log.warning(msg)


## ------------------


def cleanup_str_for_k8s(value: str):
    """
    Clean up string so that it is kubernetes-compatible: remove special chars (except "-"), and
    convert all text to lower-case.

    Args:
        value (str): The string to clean up

    Returns:
        str: The kubernetes-compatible string
    """

    value = value.replace("_", "-")
    invalid_chars = string.punctuation.replace("-", "") + string.whitespace
    chars = re.escape(invalid_chars)
    new_value = re.sub(r"[" + chars + "]", "", value).lower()
    return new_value


## ------------------


def cleanup_argo_proj_yaml(argo_proj_yaml):

    argo_proj_yaml["argocd"]["project"]["name"] = cleanup_str_for_k8s(
        argo_proj_yaml["argocd"]["project"]["name"]
    )

    argo_proj_yaml["argocd"]["parent_app"]["name"] = cleanup_str_for_k8s(
        argo_proj_yaml["argocd"]["parent_app"]["name"]
    )

    for child_app in argo_proj_yaml["argocd"]["child_apps"]["app"]:
        child_app["name"] = cleanup_str_for_k8s(child_app["name"])
        child_app["namespace"] = cleanup_str_for_k8s(child_app["namespace"])

    return argo_proj_yaml


## ------------------


def init_bootstrap(
    ctxt: Context,
    git_username: str,
    git_token: str,
    git_repo_url: str,
    argocd_username: str,
    argocd_password: str,
    target_repo_path=PARENT_REPO_PATH,
    target_environment=None,
):
    """
    Set up context variables.

    Args:
        ctxt (Context): PyInvoke Context. http://docs.pyinvoke.org/en/stable/api/context.html
        git_username (str): Git username (not required by some git providers)
        git_token (str): Git personal access token
        git_repo_url (str): Git repo HTTPS URL of the repo where the ArgoCD app definitions are located
        argocd_username (str): ArgoCD username
        argocd_password (str): ArgoCD password
        target_environment (str): Target environment to deploy to

    Raises:
        Exception: Raise exception when any of the params (except git username) is missing.
    """

    if (
        (git_token is None)
        or (git_repo_url is None)
        or (argocd_username is None)
        or (argocd_password is None)
    ):
        msg = "ERROR: Missing arg(s). Mandatory args: git-token, git-repo-url, argocd-username, argocd-password"
        publish(msg, LOG_ERROR)
        raise Exception(msg)

    # Git details
    ctxt.config["git_username"] = (
        git_username if (git_username is not None) and (git_username != "") else None
    )
    ctxt.config["git_token"] = git_token
    ctxt.config["git_repo_url"] = git_repo_url

    # ArgoCD server credentials
    ctxt.config["argocd_username"] = argocd_username
    ctxt.config["argocd_password"] = argocd_password

    ctxt.config["git_repo_path"] = target_repo_path

    # Target environment
    if target_environment is not None:
        ctxt.config["target_environment"] = target_environment.lower()


## ------------------


def process_app_template(
    app_details: dict,
    namespace: str,
    destination_cluster: str,
    project_name: str,
    destination_dir: str,
    environment: str,
    deploy_plugin=None,
):
    """
    Apply the ArgoCD application template to the given data set.

    Args:
        app_details (dict): Information about the app
        namespace (str): App's target namespace
        destination_cluster (str): App target ArgoCD cluster
        project_name (str): Name of ArgoCD project that the app belongs to
        destination_dir (str): Destination directory that transformed YAML file is written to.
        environment (str): Target environment (e.g. dev, qa, prod)
        deploy_plugin (str): Plugin to use for deployment (other than Helm or Kustomize)
    """

    env = Environment(loader=FileSystemLoader(TEMPLATES_PATH), trim_blocks=True)

    app_details["name"] = f"{app_details['name']}-app-{environment}"

    # app_details["name"] = app_details["name"]
    rendered_data = env.get_template(f"application.yml.j2").stream(
        app=app_details,
        namespace=namespace,
        destination_cluster=destination_cluster,
        project_name=f"{project_name}-{environment}",
        deploy_plugin=deploy_plugin,
    )

    filename = app_details.get("filename", f"{app_details['name']}.yml")
    rendered_data.dump(f"{destination_dir}/{filename}")
    publish(f"INFO: Created [{destination_dir}/{filename}]", LOG_INFO)


## ------------------


def get_repos(ctxt, children_only=False):

    # Get child repos
    repos_list = [
        child_app["repo_url"]
        for child_app in ctxt["argo_proj_yaml"]["argocd"]["child_apps"]["app"]
    ]

    # Add parent repo
    if not children_only:
        repos_list.append(ctxt["argo_proj_yaml"]["argocd"]["parent_app"]["repo_url"])

    # Remove duplicates from list
    repos_list = list(dict.fromkeys(repos_list))

    return repos_list


## ------------------


def clone_repo(ctxt, git_repo, target_path):

    git_provider = APP_CONFIG["git-provider"]
    git_url_prefix = f"git@{git_provider}:"
    if os.environ["ENV"] != "development":

        git_url_prefix = f"https://{git_provider}/"
        os.environ["MY_GIT_TOKEN"] = ctxt["git_token"]

        run_command(
            ctxt,
            f'git config --global url."https://$MY_GIT_TOKEN@{git_provider}/".insteadOf "https://{git_provider}/"',
        )
        publish("INFO: Set up token access for git", LOG_INFO)

        run_command(ctxt, 'git config --global user.name "ArgoCD Admin"')
        run_command(
            ctxt, f'git config --global user.email {APP_CONFIG["argocd-admin-email"]}'
        )

    git_url = git_repo.replace(f"https://{git_provider}/", git_url_prefix)
    publish(f"INFO: Using Git URL [{git_url}]", LOG_INFO)
    run_command(ctxt, f"git clone {git_url} {target_path}")
