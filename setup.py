from setuptools import find_packages, setup

_locals = {}
with open("argocd_app_bootstrap/_version.py") as fp:
    exec(fp.read(), None, _locals)
version = _locals["__version__"]

setup(
    name="argocd_app_bootstrap",
    version=version,
    url="https://github.com/d0-labs/argocd-app-bootstrap",
    author="Adriana Villela",
    author_email="adriana@dzerolabs.io",
    install_requires=["invoke"],
    packages=find_packages(exclude=["tests"]),
    include_package_data=True,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": ["argo-bootstrap = argocd_app_bootstrap.main:program.run"]
    },
)
