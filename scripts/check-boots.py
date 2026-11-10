#!/usr/bin/env python3
"""Repeat early kernel boot checks across QEMU memory configurations."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def check_case(index, directory, seconds):
    memory = (512, 1024, 2048)[index % 3]
    output = directory / f'{index + 1:03d}-{memory}'
    output.mkdir()
    result = subprocess.run([
        sys.executable, str(ROOT / 'scripts/boot-qemu.py'),
        '--seconds', str(seconds), '--memory', str(memory), '--output', str(output),
    ], capture_output=True, text=True, cwd=ROOT)
    (output / 'output.log').write_text(result.stdout + result.stderr)
    diagnostics = output / 'diagnostics.json'
    data = json.loads(diagnostics.read_text()) if diagnostics.exists() else {}
    case = {'run': index + 1, 'memory_mib': memory, 'exit': result.returncode,
            'boot': data.get('boot', {}), 'sha256': data.get('sha256', {})}
    print(f'boot {index + 1}: {memory} MiB, exit {result.returncode}', flush=True)
    return case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, default=20)
    parser.add_argument('--seconds', type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.count <= 1000 or not 1 <= args.seconds <= 3600:
        parser.error('count must be 1..1000 and seconds must be 1..3600')
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    directory = ROOT / 'build/boot/checks' / timestamp
    directory.mkdir(parents=True)
    with ThreadPoolExecutor(max_workers=2) as executor:
        cases = list(executor.map(lambda i: check_case(i, directory, args.seconds),
                                  range(args.count)))
    artifacts = {tuple(sorted(case['sha256'].items())) for case in cases}
    passed = sum(case['exit'] == 0 and case['boot'].get('platform_started') and
                 not case['boot'].get('fatal') for case in cases)
    summary = {'passed': passed, 'total': len(cases),
               'artifact_sets': len(artifacts), 'runs': cases}
    (directory / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(f'{passed}/{len(cases)} early boot checks passed; evidence: {directory}')
    if passed != len(cases) or len(artifacts) != 1:
        raise SystemExit('boot checks failed or artifacts changed during the run')


if __name__ == '__main__':
    main()
