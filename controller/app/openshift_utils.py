from kubernetes import client, config
from datetime import datetime

IN_CLUSTER = False

# Wrap the 'load_incluster' function so that when `config.load_client()` is
# called we know whether or not we are in cluster
def _load_incluster_config(**kwargs):
    IN_CLUSTER = True
    config.load_incluster_config(**kwargs)
config.load_incluster_config = _load_incluster_config

config.load_config()  # if we are in cluster, in_cluster = True
v1 = client.CoreV1Api()

secret_name = "kebechet-version-manager-{installation_id}"

if IN_CLUSTER:
    # Provided by ServiceAccountAdmissionController in kubernetes (docs: https://tinyurl.com/3snc8zj2)
    with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r") as f:
        NAMESPACE = f.read()
else:
    NAMESPACE = config.list_kube_config_contexts()[1].split("/")[0]

def _create_expiration_timestamp() -> str:
    expiration = datetime.utcnow() + datetime.hour - datetime.second * 60  # subtract 60 seconds for potential clock drift
    return expiration.strftime('%Y-%m-%dT%H:%M:%SZ')


def create_github_token_secret(installation_id: str, token: str, gh_namespace: str):  # TODO: pass token as it appears in the GithubApp library
    meta = client.V1ObjectMeta(
        annotations={"expiration": _create_expiration_timestamp()},
        labels={"app.kubernetes.io/created-by": "kebechet-version-manager"},
        name=secret_name.format(installation_id=installation_id),
    )
    secret = client.V1Secret(
        api_version="v1",
        type="Secret",
        data={"token": token, "gh_namespace": gh_namespace},
        type="Opaque",
        metadata=meta,
    )
    v1.create_namespaced_secret(namespace=NAMESPACE, body=secret)

def update_github_token_secret(installation_id: str, token: str):
    body = [
        {'op': 'replace', 'path': '/data/token', 'value': token},
        {'op': 'replace', 'path': '/metadata/annotations/expiration', _create_expiration_timestamp()}
    ]  # use json patch to alter values
    v1.patch_namespaced_secret(
        name=secret_name.format(installation_id=installation_id), namespace=NAMESPACE, body=body
    )


def delete_github_token_secret(installation_id: str):
    v1.delete_namespaced_secret(name=secret_name.format(installation_id=installation_id), namespace=NAMESPACE)