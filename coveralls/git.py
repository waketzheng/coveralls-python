from __future__ import annotations

import logging
import os
import subprocess
from typing import Any

from .exception import CoverallsException

log = logging.getLogger('coveralls.git')


def run_command(*args: str) -> str:
    try:
        cmd = subprocess.run(
            list(args),
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        raise CoverallsException(
            f'{e}\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}',
        ) from e

    return cmd.stdout.decode('utf-8').strip()


def gitlog(fmt: str) -> str:
    return run_command(
        'git',
        '--no-pager',
        'log',
        '-1',
        f'--pretty=format:{fmt}',
    )


def git_branch() -> str | None:
    branch = None
    if os.environ.get('GITHUB_ACTIONS'):
        github_ref = os.environ.get('GITHUB_REF')
        if github_ref and (
            github_ref.startswith(
                'refs/heads/',
            )
            or github_ref.startswith('refs/tags/')
        ):
            # E.g. in push events.
            branch = github_ref.split('/', 2)[-1]
        else:
            # E.g. in pull_request events.
            branch = os.environ.get('GITHUB_HEAD_REF')
    else:
        branch = (
            os.environ.get('APPVEYOR_REPO_BRANCH')
            or os.environ.get('BUILDKITE_BRANCH')
            or os.environ.get('CI_BRANCH')
            or os.environ.get('CIRCLE_BRANCH')
            or os.environ.get('GIT_BRANCH')
            or os.environ.get('TRAVIS_BRANCH')
            or os.environ.get('BRANCH_NAME')
            or run_command('git', 'rev-parse', '--abbrev-ref', 'HEAD')
        )

    return branch


def git_info() -> dict[str, dict[str, Any]]:
    """
    A hash of Git data that can be used to display more information to users.

    Example:
    -------
        "git": {
            "head": {
                "id": "5e837ce92220be64821128a70f6093f836dd2c05",
                "author_name": "Wil Gieseler",
                "author_email": "wil@example.com",
                "committer_name": "Wil Gieseler",
                "committer_email": "wil@example.com",
                "message": "depend on simplecov >= 0.7"
            },
            "branch": "master",
            "remotes": [{
                "name": "origin",
                "url": "https://github.com/lemurheavy/coveralls-ruby.git"
            }]
        }
    """
    head: dict[str, str | None]
    remotes: list[dict[str, str | None]]
    try:
        branch = git_branch()
        head = {
            'id': gitlog('%H'),
            'author_name': gitlog('%aN'),
            'author_email': gitlog('%ae'),
            'committer_name': gitlog('%cN'),
            'committer_email': gitlog('%ce'),
            'message': gitlog('%s'),
        }
        remotes = [
            {'name': line.split()[0], 'url': line.split()[1]}
            for line in run_command('git', 'remote', '-v').splitlines()
            if '(fetch)' in line
        ]
    except (CoverallsException, OSError) as ex:
        # When git is not available, try env vars as per Coveralls docs:
        # https://docs.coveralls.io/mercurial-support
        # Additionally, these variables have been extended by GIT_URL and
        # GIT_REMOTE
        branch = os.environ.get('GIT_BRANCH')
        head = {
            'id': os.environ.get('GIT_ID'),
            'author_name': os.environ.get('GIT_AUTHOR_NAME'),
            'author_email': os.environ.get('GIT_AUTHOR_EMAIL'),
            'committer_name': os.environ.get('GIT_COMMITTER_NAME'),
            'committer_email': os.environ.get('GIT_COMMITTER_EMAIL'),
            'message': os.environ.get('GIT_MESSAGE'),
        }
        remotes = [
            {
                'name': os.environ.get('GIT_REMOTE'),
                'url': os.environ.get('GIT_URL'),
            },
        ]
        if not all(head.values()):
            log.warning(
                'Failed collecting git data. Are you running coveralls inside '
                'a git repository? Is git installed?',
                exc_info=ex,
            )
            return {}

    return {
        'git': {
            'branch': branch,
            'head': head,
            'remotes': remotes,
        },
    }
