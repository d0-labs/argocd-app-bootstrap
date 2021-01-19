#! /usr/bin/env python3
# -*- coding: utf-8 -*-


# Invoke magic
from invoke import Collection, task

import argocd_app_bootstrap.tasks.common.actions as common_actions
import argocd_app_bootstrap.tasks.argocd.setup.actions as argo_setup_actions
import argocd_app_bootstrap.tasks.argocd.run.actions as argo_un_actions
import argocd_app_bootstrap.tasks.deploy.setup.actions as scaffold_actions

ns = Collection(
    common=common_actions,
    argo_setup=argo_setup_actions,
    argo_run=argo_un_actions,
    deploy_setup=scaffold_actions,
)
