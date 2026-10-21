"""Offline installation checks: no real sources, config, or services."""
import json
from pathlib import Path
import plistlib
import tempfile
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import install
import ledger


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Path(tempfile.mkdtemp(prefix='cairn-install-test-')) / 'runtime'

    def test_fresh_install_and_upgrade_preserve_private_state(self):
        install.install(self.runtime)
        config = self.runtime / 'config.json'
        self.assertFalse(json.loads(config.read_text())['classification_enabled'])
        config.write_text('{"private": "fictional-local-value"}')
        state = self.runtime / 'state.json'
        state.write_text('{"cursor": 42}')
        old = (self.runtime / 'ledger.py').read_bytes()
        install.install(self.runtime, code_only=True)
        self.assertEqual(config.read_text(), '{"private": "fictional-local-value"}')
        self.assertEqual(state.read_text(), '{"cursor": 42}')
        self.assertEqual(next((self.runtime/'backups').glob('*/ledger.py')).read_bytes(), old)
        plist = plistlib.loads((self.runtime/'com.cairn.ledger.plist').read_bytes())
        self.assertEqual(plist['ProgramArguments'][1], str(self.runtime.resolve()/'watch-ledger'))
        self.assertNotIn('__RUNTIME__', str(plist))

    def test_code_only_requires_existing_config(self):
        with self.assertRaises(ValueError):
            install.install(self.runtime, code_only=True)
        self.assertFalse(self.runtime.exists())

    def test_reject_runtime_inside_repository(self):
        with self.assertRaises(ValueError):
            install.install(Path(__file__).resolve().parents[1] / 'runtime')

    def test_main_expands_example_paths_without_reading_sources(self):
        install.install(self.runtime)
        with patch('sys.argv', ['ledger.py', 'scan', '--home', str(self.runtime)]), patch.object(ledger, 'discover', return_value={}) as discover:
            self.assertEqual(ledger.main(), 0)
        config = discover.call_args.args[0]
        self.assertTrue(Path(config['vault']).is_absolute())
        self.assertTrue(all(Path(p).is_absolute() for roots in config['sources'].values() for p in roots))

    def test_view_uses_configured_backfill(self):
        self.runtime.mkdir(parents=True)
        ledger.render({'vault':str(self.runtime),'sources':{},'since':'2025-02-03T00:00:00Z'}, {}, [])
        self.assertIn('2025-02-03 08:00', (self.runtime/'regressions.md').read_text())


if __name__ == '__main__':
    unittest.main()
