import os

from flask import Flask
from flask_githubapp import GitHubApp
from github3.repos.repo import Repository

from . import openshift_utils
app = Flask(__name__)

app.config['GITHUBAPP_ID'] = int(os.environ['GITHUBAPP_ID'])
with open(os.environ['GITHUBAPP_KEY_PATH'], 'rb') as key_file:
    app.config['GITHUBAPP_KEY'] = key_file.read()
app.config['GITHUBAPP_SECRET'] = os.environ['GITHUBAPP_SECRET']
app.config['GITHUBAPP_ROUTE'] = '/github/'  # allows for extension to other git forges

app.config['REPOSITORY_CONFIG_DIR'] = os.environ['REPOSITORY_CONFIG_DIR']  # TODO: generate named temp directory as default

github_app = GitHubApp(app)

def _push_is_for_default_branch(github_app: GitHubApp):
    default_branch = github_app.payload["default_branch"]
    updated_ref: str = github_app.payload["ref"]
    ref_parts = updated_ref.split("/")
    return ref[1] == "heads" and ref[2] == default_branch  # updated a branch && updated branch is project's default


def _get_repository_as_installation() -> Repository: 
    return github_app.installation_client.repository(
        owner=github_app.payload["repository"]["owner"]["name"],
        repository=github_app.payload["repository"]["name"]
    )


# TODO: CONFIGURATION: for now get core event loop down then worry about configuration for PRs and whatnot
# TODO: where should configuration be? should configuration be per repository, or should it be org wide and live in the .github repository
# TODO: what file structure do we use for storing configuration for repositories?

# TODO: instantiate worker which updates version string, writes changelog and opens PR when issue is opened
# from this issue we just need to know: what type of release, and optionally a specific commit can be passed

# TODO: listen for merge events for PRs created by the app, when merged create a new tag release with the appropriate version string on the appropriate commit


# TODO: change this to download version manager specific config
def update_config_file_on_change():
    if not _push_is_for_default_branch(github_app):
        return
    repo_owner = github_app.payload["repository"]["owner"]["name"]
    repo_name = github_app.payload["repository"]["name"]
    repository = _get_repository_as_installation()
    for commit in github_app.payload["commits"]:
        if ".thoth.yaml" in commit["modified"]:
            with open(
                os.path.join(app.config['REPOSITORY_CONFIG_DIR'], repo_owner, repo_name, ".thoth.yaml"), "w"
            ) as f:
                f.write(repository.file_contents(".thoth.yaml").decoded.decode('utf-8'))
        if ".github/kebechet-advise-manager" in commit["modified"]:
            with open(
                os.path.join(app.config['REPOSITORY_CONFIG_DIR'], repo_owner, repo_name, "app_config"), "w"
            ) as f:
                f.write(repository.file_contents(".github/kebechet-advise-manager").decoded.decode('utf-8'))


@github_app.on("issue.opened")
def create_new_version_pr():
    # TODO: check if issue opener has permission
    # TODO: schedule worker open_version_update_pr(repository, update_type, issue_id)
    pass

@github_app.on("push")
def process_push_webhook():
    update_config_file_on_change()  # should happen first so config is always latest before acting


# TODO: create the .github repo if it doesn't exist
# TODO: add issue templates to the .github repo
@github_app.on("installation.created")
def install_app():
    openshift_utils.create_github_token_secret(
        installation_id=github_app.installation_id,
        token=github_app.installation_token,
        gh_namespace=github_app.payload["installation"]["account"]["login"],
    )


@github_app.on("installation.deleted")
def uninstall_app():
    openshift_utils.delete_github_token_secret(installation_id=github_app.installation_id)
