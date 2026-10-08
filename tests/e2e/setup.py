"""Fetch pinned upstream validators and install the E2E browser (macOS/Linux)."""
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def run(*args, cwd=ROOT):
    subprocess.run(args, cwd=cwd, check=True)


if __name__ == '__main__':
    deps = ROOT / '.e2e-deps'
    deps.mkdir(exist_ok=True)
    for name, spec in json.loads((HERE / 'repos.json').read_text()).items():
        target = deps / name
        if not target.exists():
            run('git', 'clone', spec['url'], str(target))
        head = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=target, text=True).strip()
        dirty = subprocess.check_output(
            ['git', 'status', '--porcelain', '--untracked-files=no'],
            cwd=target, text=True).strip()
        if dirty:
            raise SystemExit(f'{target} has modified tracked files; preserve them before setup.')
        if head != spec['revision']:
            run('git', 'fetch', 'origin', spec['revision'], cwd=target)
        run('git', 'checkout', '--detach', spec['revision'], cwd=target)
    run('make', 'abc2midi', cwd=deps / 'abcmidi')
    run('npm', 'ci', '--ignore-scripts', cwd=HERE)
    run('npx', '--no-install', 'playwright', 'install', 'chromium', cwd=HERE)
