#!/usr/bin/env python3
"""Static, fail-closed integrity check of a locked npm install plan.

This is NOT npm audit, a download integrity check or a vulnerability scan.
"""
from __future__ import annotations
import argparse
import base64
import binascii
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
if __package__:
    from .evidence_integrity_vlab import load_json, EvidenceError
else:
    from evidence_integrity_vlab import load_json, EvidenceError

SEMVER_LIKE = re.compile(r'^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.+-]+)?$')
INTEGRITY = re.compile(r'^(?:sha512|sha384|sha256)-[A-Za-z0-9+/=]+(?:\s+(?:sha512|sha384|sha256)-[A-Za-z0-9+/=]+)*$')

def _strong_integrity(value: object) -> bool:
    """SRI entries must decode to complete hashes, not just match base64 syntax."""
    if not isinstance(value, str) or not INTEGRITY.fullmatch(value):
        return False
    lengths = {'sha256': 32, 'sha384': 48, 'sha512': 64}
    try:
        return all(
            len(base64.b64decode(encoded, validate=True)) == lengths[algorithm]
            for algorithm, encoded in (part.split('-', 1) for part in value.split())
        )
    except (ValueError, KeyError, binascii.Error):
        return False


def scan(data:dict, manifest: dict | None = None)->dict:
    issues=[]
    if data.get('lockfileVersion') != 3 or not isinstance(data.get('packages'),dict):
        return {'validated':False,'package_count':0,'issues':['unsupported_lockfile_or_missing_packages'],
                'scope':'Static npm lock integrity only; not SCA or runtime attestation.'}
    pkgs=data['packages']
    if not isinstance(pkgs.get(''),dict):
        issues.append('missing_root_package')
    if manifest is not None:
        if not isinstance(manifest, dict):
            issues.append('invalid_package_manifest')
        else:
            root = pkgs.get('', {})
            for group in ('dependencies', 'devDependencies', 'optionalDependencies'):
                actual = manifest.get(group, {})
                locked = root.get(group, {}) if isinstance(root, dict) else None
                if not isinstance(actual, dict) or actual != locked:
                    issues.append('manifest_lock_drift:'+group)
            if manifest.get('name') != root.get('name') or manifest.get('version') != root.get('version'):
                issues.append('manifest_lock_drift:identity')
            for group in ('dependencies', 'devDependencies'):
                for name in manifest.get(group, {}) if isinstance(manifest.get(group, {}), dict) else ():
                    if 'node_modules/' + name not in pkgs:
                        issues.append('missing_direct_package:'+str(name)[:80])
    packages=0;install_scripts=0; install_names=[]
    for location,info in sorted(pkgs.items()):
        if location=='': continue
        if not location.startswith('node_modules/') or not isinstance(info,dict):
            issues.append('malformed_package_entry:'+str(location)[:100]);continue
        packages+=1
        if info.get('hasInstallScript') is True:
            install_scripts+=1
            install_names.append(location)
        if info.get('link') is True:
            issues.append('unreviewed_symlink_package:'+location);continue
        version=info.get('version')
        if not isinstance(version,str) or not SEMVER_LIKE.fullmatch(version):
            issues.append('unlocked_version:'+location)
        resolved=info.get('resolved')
        if not isinstance(resolved,str) or not resolved.startswith('https://'):
            issues.append('non_https_or_missing_tarball:'+location)
        else:
            try:
                parsed=urlsplit(resolved)
                safe_url = (bool(parsed.hostname) and not parsed.username and not parsed.password
                            and not parsed.fragment and not parsed.query and parsed.port in (None,443))
            except ValueError:
                safe_url = False
            if not safe_url:
                issues.append('unsafe_tarball_url:'+location)
        integrity=info.get('integrity')
        if not _strong_integrity(integrity):
            issues.append('missing_or_weak_integrity:'+location)
    if packages < 1: issues.append('empty_locked_dependencies')
    return {'validated':not issues,'package_count':packages,'install_script_packages':install_scripts,'install_script_locations':install_names,
            'issues':issues[:100], 'issue_count':len(issues),
            'scope':'Static npm package-lock structural integrity; excludes SCA, fetched bytes and bundle exposure.'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--lock',type=Path,default=Path(__file__).resolve().parents[1]/'frontend/package-lock.json')
    p.add_argument('--manifest',type=Path,default=Path(__file__).resolve().parents[1]/'frontend/package.json')
    p.add_argument('--output',type=Path)
    args=p.parse_args(argv)
    try:
        data=load_json(args.lock)
        result=scan(data,load_json(args.manifest))
        result['lock_sha256']=hashlib.sha256(args.lock.read_bytes()).hexdigest()
        result['manifest_sha256']=hashlib.sha256(args.manifest.read_bytes()).hexdigest()
    except (OSError,EvidenceError) as exc:
        result={'validated':False,'issues':['invalid_lockfile:'+type(exc).__name__],
                'scope':'Static npm lock integrity; cannot inspect dependencies'}
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return 0 if result['validated'] else 1

if __name__=='__main__':sys.exit(main())
