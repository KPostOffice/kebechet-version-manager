from git import Repo
# TODO: create command for updating version and changelog

# TODO: clone repo using tekton

@click.command()
@click.option('--repo-namespace')
@click.option('--repo-name')
@click.option('--release-type')
@click.option('--commit-hash')
@click.option('--repo-location')
def update_version():