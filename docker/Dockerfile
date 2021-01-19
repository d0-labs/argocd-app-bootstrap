# We need a base image running python3.7 since our slim ubuntu phusion image installed 3.6 by default and it was voodoo to try to get 3.7
FROM python:3.8.5-slim-buster

RUN apt-get update && apt-get -y install \
    gcc \
    apt-transport-https \
    curl \
    gnupg2 \
    wget \
    git-all

# Install kubectl
RUN curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
RUN echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list
RUN apt-get update && apt-get install -y kubectl

# Install gcloud & additional components
RUN curl -sSL https://sdk.cloud.google.com > /tmp/gcl && bash /tmp/gcl --install-dir=/usr/local/bin/gcloud --disable-prompts
ENV PATH=$PATH:/usr/local/bin/gcloud/google-cloud-sdk/bin
RUN gcloud components update -q && \
    gcloud components install alpha -q && \
    gcloud components install beta -q

# Set up working directory
ENV WORKDIR="/workdir"
RUN mkdir -p ${WORKDIR}
WORKDIR ${WORKDIR}

# Python package
ARG ARGOCD_APP_BOOTSTRAP
COPY "argocd_app_bootstrap-${ARGOCD_APP_BOOTSTRAP}-py3-none-any.whl" .

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

RUN pip install "argocd_app_bootstrap-${ARGOCD_APP_BOOTSTRAP}-py3-none-any.whl"

# Install ArgoCD CLI
COPY argocd-linux-amd64 /usr/local/bin/argocd
RUN chmod +x /usr/local/bin/argocd

# gcloud credentials
COPY gcloud-sa.json .

COPY startup.sh .
RUN chmod 755 startup.sh

# CMD ["/workdir/startup.sh"]
CMD ["/bin/bash"]