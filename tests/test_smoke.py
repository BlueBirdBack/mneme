import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / 'tests' / 'fixtures' / 'workspace'
SCRIPTS = REPO / 'scripts'


def run_json(cmd: list[str]) -> dict:
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.returncode != 0:
        raise AssertionError(f"Command failed ({cp.returncode}): {' '.join(cmd)}\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}")
    return json.loads(cp.stdout)


class MnemeSmokeTests(unittest.TestCase):
    def make_workspace(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix='mneme-test-'))
        ws = tmp / 'workspace'
        shutil.copytree(FIXTURE, ws)
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        return ws

    def test_ingest_fixture_workspace(self) -> None:
        ws = self.make_workspace()
        raw_out = ws / 'raw-out'
        data = run_json([
            sys.executable,
            str(SCRIPTS / 'mneme_ingest_memory.py'),
            '--root', str(ws),
            '--out', str(raw_out),
        ])
        self.assertGreaterEqual(data['sourceCount'], 2)
        self.assertGreater(data['itemCount'], 0)
        self.assertTrue((raw_out / 'sources.jsonl').exists())
        self.assertTrue((raw_out / 'items.jsonl').exists())

    def test_compile_fixture_raw_into_outputs(self) -> None:
        ws = self.make_workspace()
        raw_out = ws / 'raw-out'
        compiled_out = ws / 'compiled-out'
        run_json([
            sys.executable,
            str(SCRIPTS / 'mneme_ingest_memory.py'),
            '--root', str(ws),
            '--out', str(raw_out),
        ])
        cp = subprocess.run([
            sys.executable,
            str(SCRIPTS / 'mneme_compile_memory.py'),
            '--root', str(ws),
            '--raw', str(raw_out),
            '--out', str(compiled_out),
        ], capture_output=True, text=True)
        if cp.returncode != 0:
            raise AssertionError(f"Compile failed ({cp.returncode})\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}")
        self.assertTrue((compiled_out / 'projects.md').exists())
        self.assertTrue((compiled_out / 'people.md').exists())
        self.assertTrue((compiled_out / 'timeline.md').exists())
        self.assertIn('Project Alpha', (compiled_out / 'projects.md').read_text())
        self.assertIn('Compiled Memory — People', (compiled_out / 'people.md').read_text())
        self.assertTrue((compiled_out / 'documents.jsonl').exists())
        self.assertTrue((compiled_out / 'entries.jsonl').exists())

    def test_runtime_prepare_people_category(self) -> None:
        ws = self.make_workspace()
        raw_out = ws / 'runtime-raw'
        bundles_out = ws / 'runtime-bundles'
        materialize_out = ws / 'runtime-materialized'
        data = run_json([
            sys.executable,
            str(SCRIPTS / 'mneme_runtime_orchestrate.py'),
            'prepare-task',
            '--root', str(ws),
            '--category', 'people',
            '--raw-out', str(raw_out),
            '--bundles-out', str(bundles_out),
            '--materialize-out', str(materialize_out),
        ])
        self.assertEqual(data['category'], 'people')
        self.assertEqual(data['bundleMeta']['category'], 'people')
        self.assertGreater(data['bundleMeta']['itemCount'], 0)
        self.assertTrue(Path(data['bundleFile']).exists())
        self.assertIn('Category: people', data['taskPrompt'])


if __name__ == '__main__':
    unittest.main()
