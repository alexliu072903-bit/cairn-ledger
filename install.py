#!/usr/bin/env python3
"""Copy only distributable code; never start a service or enable classification."""
import argparse
import datetime as dt
import os
from pathlib import Path
import plistlib
import shutil
import sys

FILES = {
    'ledger.py': 'ledger.py',
    'process-ledger': 'bin/process-ledger',
    'watch-ledger': 'bin/watch-ledger',
    'classifier.schema.json': 'schemas/classifier.schema.json',
}


def install(runtime, code_only=False):
    source = Path(__file__).resolve().parent
    runtime = runtime.expanduser().resolve()
    if runtime == source or source in runtime.parents:
        raise ValueError('runtime must be outside the source repository')
    if code_only and not (runtime / 'config.json').is_file():
        raise ValueError('--code-only requires an existing runtime config.json')
    runtime.mkdir(parents=True, exist_ok=True)
    backup = runtime / 'backups' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    for name, relative in FILES.items():
        target = runtime / name
        if target.exists():
            backup.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup / name)
        pending = runtime / (name + '.install-tmp')
        shutil.copy2(source / relative, pending)
        os.replace(pending, target)
    if not code_only:
        config = runtime / 'config.json'
        if not config.exists():
            # Exclusive creation preserves any concurrent/local configuration.
            with config.open('x') as f:
                f.write((source / 'config.example.json').read_text())
            config.chmod(0o600)
        (runtime / 'logs').mkdir(exist_ok=True)
        template = plistlib.loads((source / 'launchd' / 'com.cairn.ledger.plist.template').read_bytes())
        template['ProgramArguments'] = [sys.executable, str(runtime / 'watch-ledger')]
        template['WorkingDirectory'] = str(runtime)
        template['StandardOutPath'] = str(runtime / 'logs' / 'launchd.log')
        template['StandardErrorPath'] = str(runtime / 'logs' / 'launchd.log')
        (runtime / 'com.cairn.ledger.plist').write_bytes(plistlib.dumps(template))
    print('Code installed at ' + str(runtime) + '; no service started. Existing config and data preserved.')


if __name__ == '__main__':
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, default=Path.home() / '.codex/ledger')
    parser.add_argument('--code-only', action='store_true', help='Update code only; preserve service definition and config')
    args = parser.parse_args()
    install(args.runtime, args.code_only)
