#! /bin/bash

gcloud auth activate-service-account <service_account_name> --key-file=<path_to_key_file_json>
gcloud config set project <project_name>
gcloud container clusters get-credentials <cluster_name> --region=<region_name>

