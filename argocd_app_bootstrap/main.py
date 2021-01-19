from . import *

from ._version import __version__
from invoke import Program


version = __version__

program = Program(
    name="ArgoCD App Bootstrap",
    namespace=ns,
    version=version,
    binary="argo-bootstrap",
    binary_names=["argo-bootstrap"],
)
