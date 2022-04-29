from git import Repo
import click
import semver
from github import Github

import re
from datetime import datetime
import yaml
import contextlib
from pathlib import Path
import os

from common.enums import ReleaseType


# TODO: clone repo using tekton

# TODO: mount ssh and known hosts for pushing to new branch


VERSION_UPDATE_DISPATCH = {
    ReleaseType.patch.value: lambda v: semver(v).bump_patch(),
    ReleaseType.minor.value: lambda v: semver(v).bump_minor(),
    ReleaseType.major.value: lambda v: semver(v).bump_major(),
    ReleaseType.pre.value: lambda v: semver(v).bump_prerelease(),
    ReleaseType.build.value: lambda v: semver(v).bump_build(),
    ReleaseType.finalize.value: lambda v: semver(v).finalize_version(),
    ReleaseType.calendar.value: lambda _: datetime.utcnow().strftime('%Y.%m.%d'),
}


ACCESS_TOKEN = os.getenv("APP_INSTALLATION_TOKEN")


@contextlib.contextmanager
def working_dir(path):
    try:
        cur_dir = os.getcwd()
        yield os.chdir(path)
    finally:
        os.chdir(cur_dir)


def update_version_str_in_files(prev_release, new_release, files_to_update):
    for f_name in files_to_update:
        path = Path(f_name)
        if not path.exists():
            continue  # TODO: might be useful to open an issue warning the user in this case
        with open(f_name, 'r') as f:
            contents = f.read()
        contents.replace(prev_release, new_release)
        with open(f_name, 'w+') as f:
            f.write(contents)
        repo.index.add([f_name])

def update_changelog(repo: Repo, old_ref, new_ref, new_release):
    if old_ref is None:  # git initial commit
        old_ref = repo.git.rev_list('HEAD', max_parents=0)
    changelog = repo.git.log(f'{old_ref}..{new_ref}', no_merges=True, format='%h %s').splitlines()
    with open('CHANGELOG.md', 'a+') as f:  # creates file if it doesn't exist without overwriting it
        f.seek(0, 0)  # seek back to beginning since append puts files position at the very end
        lines = f.readlines()
        f.seek(0, 0)
        if len(lines) > 0 and lines[0].startswith('# '):  # checking if title its a title of type "# Title"
            f.write(lines.pop(0))
        elif (len(lines) > 1 and lines[1][0] == '='):  # Checking if its a title of type "Title \n ===="
            f.write(lines.pop(0) + lines.pop(0))  # Pop title and underline
        f.write(
            f"\n## Release v{new_release} ({datetime.now().replace(microsecond=0).isoformat()})\n"
        )
        f.write("\n".join(changelog) + "\n")
        f.write("".join(lines))


@click.group()
def cli():
    pass

@cli.command()
@click.option('--repo-namespace', type=str)
@click.option('--repo-name', type=str)
@click.option('--release-type', type=int)
@click.option('--repo-location', type=click.types.Path(exists=True))
@click.option('--trigger-id', type=int)
@click.option('--commit-hash', default='HEAD')
@click.option('--yaml-config', default='')
def update_version(repo_namespace, repo_name, release_type, repo_location, trigger_id, commit_hash, yaml_config):
    config = yaml.safe_load(yaml_config) or dict()
    repo = Repo(repo_location)
    files_to_update = config.get('files-with-version', ['VERSION'])
    if not repo.git.tag('-l'):  # initial release
        prev_release = None
        new_release = "0.0.0"
    else:
        prev_release = repo.git.tag('--list', '--sort=-version:refname', 'v*').splitlines()[0]  # git latest vers. tag
        try:
            new_release = VERSION_UPDATE_DISPATCH[release_type](prev_release)
        except ValueError as exc:
            pass  # TODO: handle value error when semver cannot parse previous release

    branch_name = f'kebechet-version-update-v{new_release}'
    repo.git.checkout('-b', branch_name)
    with working_dir(repo_location):
        update_changelog(repo=repo, old_ref=prev_release, new_ref=commit_hash, new_release=new_release)
        repo.index.add(['CHANGELOG.md'])

        if prev_release:  # cannot update version strings during initial release (No version string to replace)
            update_version_str_in_files(
                prev_release=prev_release, new_release=new_release, files_to_update=files_to_update
            )

    repo.index.commit(f'Version v{new_release} Release')
    repo.remote().push(branch_name)

    g = Github(ACCESS_TOKEN)
    github_repo = g.get_repo(f"{repo_namespace}/{repo_name}")
    github_repo.create_pull(
        title=f'Version v{new_release}',
        body=f"Automatic changelog and version string updates. Triggered by #{trigger_id}",
        base=github_repo.default_branch,
        head=branch_name,
    )

if __name__ == '__main__':
    cli(auto_envvar_prefix='KEBECHET')
