import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
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

    def compile_workspace(self, ws: Path) -> Path:
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
        return compiled_out

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
        compiled_out = self.compile_workspace(ws)
        projects_text = (compiled_out / 'projects.md').read_text()
        people_text = (compiled_out / 'people.md').read_text()
        self.assertTrue((compiled_out / 'projects.md').exists())
        self.assertTrue((compiled_out / 'people.md').exists())
        self.assertTrue((compiled_out / 'timeline.md').exists())
        self.assertIn('Project Alpha', projects_text)
        self.assertNotIn('## Active Projects', projects_text)
        self.assertIn('Compiled Memory — People', people_text)
        self.assertIn('What to call them', people_text)
        self.assertTrue((compiled_out / 'documents.jsonl').exists())
        self.assertTrue((compiled_out / 'entries.jsonl').exists())

    def test_compile_demotes_generic_sections_and_prefers_system_subheadings(self) -> None:
        ws = self.make_workspace()
        extra_note = ws / 'memory' / '2026-04-01-routing.md'
        extra_note.write_text(
            '# 2026-04-01\n\n'
            '## Aqua-CQ Project\n\n'
            '### Server Access\n'
            '- Hostname: iv-ydyut13e9ss6ipm2he1t\n'
            '- Ubuntu 24.04.4, 8GB RAM, 40GB disk\n'
            '- Project at /opt/aqua-cq (backend only), frontend deployed to /var/www/html/cq/\n\n'
            '### Three services on the box\n'
            '- :8003 — aqua-qdh (backend-dev, /opt/aqua-qdh)\n\n'
            '## Deploy process (correct)\n\n'
            '```bash\n'
            '# Build\n'
            'export PATH="$HOME/.openclaw/tools/node-v22.22.0/bin:$PATH"\n'
            'cd /opt/aqua-cq && npm run build\n'
            '```\n',
            encoding='utf-8',
        )

        compiled_out = self.compile_workspace(ws)
        projects_text = (compiled_out / 'projects.md').read_text()
        systems_text = (compiled_out / 'systems.md').read_text()

        self.assertNotIn('## Build', projects_text)
        self.assertNotIn('## Hostname', projects_text)
        self.assertNotIn('## Ubuntu 24.04.4, 8GB RAM, 40GB disk', projects_text)
        self.assertNotIn('## :8003 — aqua-qdh (backend-dev, /opt/aqua-qdh)', projects_text)
        self.assertIn('## Server Access — Hostname', systems_text)
        self.assertIn('## Ubuntu 24.04.4, 8GB RAM, 40GB disk', systems_text)
        self.assertIn('## :8003 — aqua-qdh (backend-dev, /opt/aqua-qdh)', systems_text)

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
            '--allow-agent-export',
        ])
        self.assertEqual(data['category'], 'people')
        self.assertEqual(data['bundleMeta']['category'], 'people')
        self.assertGreater(data['bundleMeta']['itemCount'], 0)
        self.assertTrue(Path(data['bundleFile']).exists())
        self.assertIn('Category: people', data['taskPrompt'])

    def test_retrieval_returns_citations(self) -> None:
        ws = self.make_workspace()
        raw_out = ws / 'raw-out'
        run_json([
            sys.executable,
            str(SCRIPTS / 'mneme_ingest_memory.py'),
            '--root', str(ws),
            '--out', str(raw_out),
        ])
        data = run_json([
            sys.executable,
            str(SCRIPTS / 'mneme_retrieve.py'),
            '--root', str(ws),
            '--raw', str(raw_out),
            '--query', 'Project Alpha',
            '--json',
        ])
        self.assertGreaterEqual(data['count'], 1)
        self.assertIn('citation', data['results'][0])
        self.assertTrue(data['results'][0]['citation']['path'])

    def test_activity_mode_surfaces_git_and_session_history(self) -> None:
        ws = self.make_workspace()
        repo = ws / 'project-repo'
        repo.mkdir()
        subprocess.run(['git', 'init', str(repo)], check=True, capture_output=True, text=True)
        subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Mneme Test'], check=True, capture_output=True, text=True)
        subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 'mneme@example.com'], check=True, capture_output=True, text=True)
        (repo / 'notes.txt').write_text('timeline retrieval fix\n', encoding='utf-8')
        subprocess.run(['git', '-C', str(repo), 'add', 'notes.txt'], check=True, capture_output=True, text=True)
        commit_env = os.environ.copy()
        now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        commit_env['GIT_AUTHOR_DATE'] = now_iso
        commit_env['GIT_COMMITTER_DATE'] = now_iso
        subprocess.run([
            'git', '-C', str(repo), 'commit', '-m', 'fix: add recent activity retrieval'
        ], check=True, capture_output=True, text=True, env=commit_env)

        session_root = ws / 'agents'
        sessions_dir = session_root / 'codex' / 'sessions'
        sessions_dir.mkdir(parents=True)
        session_event = {
            'ts': now_iso.replace('+00:00', 'Z'),
            'epochMs': 1775610000000,
            'agentId': 'codex',
            'kind': 'system_event',
            'childSessionKey': 'agent:codex:acp:test',
            'text': 'codex: traced recent activity through git and child sessions',
        }
        (sessions_dir / 'sample.acp-stream.jsonl').write_text(json.dumps(session_event) + '\n', encoding='utf-8')

        data = run_json([
            sys.executable,
            str(SCRIPTS / 'mneme_retrieve.py'),
            '--root', str(ws),
            '--session-root', str(session_root),
            '--mode', 'activity',
            '--query', 'what did you do in the last 24 hours',
            '--json',
        ])
        self.assertEqual(data['mode'], 'activity')
        self.assertGreaterEqual(data['sourceCounts'].get('git', 0), 1)
        self.assertGreaterEqual(data['sourceCounts'].get('sessions', 0), 1)
        kinds = {row['kind'] for row in data['results']}
        self.assertIn('git_commit', kinds)
        self.assertIn('session_system_event', kinds)


if __name__ == '__main__':
    unittest.main()
