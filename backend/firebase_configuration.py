"""Fail-closed Firebase configuration checks for the original CourseSphere backend.

No external services or Firebase SDK are needed to validate the configuration.
Emulator mode deliberately accepts *only* explicit loopback host:port pairs,
not URLs, credentials-in-authority, suffixes, path or query components.
"""
from __future__ import annotations

import os
import re
from urllib.parse import urlsplit

_DEMO_PROJECT = re.compile(r'^demo-[A-Za-z0-9-]{1,80}$')
_DNS_LABEL = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$', re.IGNORECASE)
_LOOPBACK = re.compile(r'^(?:localhost|127\.0\.0\.1|\[::1\]):([0-9]{1,5})$', re.IGNORECASE)


def emulator_host(value: str, setting: str) -> str:
    """Return the verbatim host:port; no normalization or URL rewriting."""
    if not isinstance(value, str):
        raise RuntimeError(f'{setting} must be an explicit loopback host:port')
    found = _LOOPBACK.fullmatch(value)
    if not found or not 1 <= int(found.group(1)) <= 65535:
        raise RuntimeError(f'{setting} must be an explicit loopback host:port')
    return value


def validate_emulators(project: str, auth_host: str, db_host: str, credential_file: str) -> None:
    if (not isinstance(project, str) or not _DEMO_PROJECT.fullmatch(project)
            or project.endswith('-') or '--' in project):
        raise RuntimeError('Emulator mode requires a valid demo-* GCLOUD_PROJECT')
    # Container-to-container traffic is explicitly opt-in, and ONLY a fixed
    # service DNS name on the pre-validated local Docker network is accepted.
    # The standard/default path remains strict loopback-only.
    docker_mode = os.getenv('COURSESPHERE_DOCKER_EMULATOR_MODE', '0')
    if docker_mode == '1':
        if (auth_host != 'official_firebase_emulators:9099'
                or db_host != 'official_firebase_emulators:9000'):
            raise RuntimeError('Container emulators require fixed internal service names')
    elif docker_mode == '0':
        emulator_host(auth_host, 'FIREBASE_AUTH_EMULATOR_HOST')
        emulator_host(db_host, 'FIREBASE_DATABASE_EMULATOR_HOST')
    else:
        raise RuntimeError('Invalid container emulator opt-in value')
    if credential_file:
        raise RuntimeError('Service-account credentials must not be loaded in emulator mode')


def validate_live(credential_file: str, database_url: str, auth_host: str, db_host: str) -> None:
    """Allow only an explicit HTTPS RTDB endpoint in non-emulator mode.

    This is input validation, not permission to contact the endpoint: external
    credentials and publication remain operator-controlled.
    """
    if auth_host or db_host:
        raise RuntimeError('Emulator hosts require explicit emulator mode')
    if not isinstance(credential_file, str) or not credential_file.strip():
        raise RuntimeError('Explicit credential path required')
    if not isinstance(database_url, str) or any(ch.isspace() for ch in database_url):
        raise RuntimeError('Explicit HTTPS Firebase database URL required')
    try:
        parts = urlsplit(database_url)
        valid = (parts.scheme == 'https' and bool(parts.hostname)
                 and parts.port in (None, 443)
                 and parts.username is None and parts.password is None
                 and not parts.path.strip('/') and not parts.query and not parts.fragment
                 and not database_url.endswith('?') and not database_url.endswith('#')
                 and parts.hostname.endswith(('.firebaseio.com', '.firebasedatabase.app'))
                 and parts.hostname.count('.') >= 2
                 and all(_DNS_LABEL.fullmatch(label) for label in parts.hostname.split('.')))
    except ValueError:
        valid = False
    if not valid:
        raise RuntimeError('Explicit HTTPS Firebase database URL required')


def validate_existing_default_app(app: object, project_id: str, database_url: str,
                                  *, emulator: bool, emulator_credential_type: type | None = None) -> None:
    """Never silently reuse a process-global Firebase app for another project.

    In emulator mode also reject a preconfigured production credential, even
    when the project name was accidentally copied to a demo-* string.
    """
    options = getattr(app, 'options', None)
    if not isinstance(options, dict):
        raise RuntimeError('Existing Firebase app lacks verifiable configuration')
    if options.get('databaseURL') != database_url:
        raise RuntimeError('Existing Firebase app points at another database')
    if project_id and options.get('projectId') != project_id:
        raise RuntimeError('Existing Firebase app points at another project')
    if emulator and (emulator_credential_type is None
                     or not isinstance(getattr(app, 'credential', None), emulator_credential_type)):
        raise RuntimeError('Existing Firebase app was not configured with emulator credentials')
