#!/usr/bin/env python3
"""Refresh/check the maintained forecast dependency manifest after source upgrades.

Run: python src/forecast_source_manifest.py --write (maintainer), or --check.
Imports and literal worker filenames are followed without executing modules.
Generated studies, trial records and model artifacts are never included.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path


def build(project):
    src=Path(project)/'src';files={p.relative_to(src).as_posix():p for p in src.rglob('*.py')}
    queue=['reissue_forecast_report.py','forecast_cli.py','forecast_source_manifest.py','run_global_recursive_forecast.py','run_causal_japan_energy.py','audit_causal_japan_energy.py','audit_japan_energy_replay.py','audit_energy_temporal_availability.py']
    seen=set()
    def add(module):
        if module=='src':return
        if module.startswith('src.'):module=module[4:]
        parts=module.split('.')
        for i in range(1,len(parts)+1):
            stem='/'.join(parts[:i])
            for name in [stem+'.py',stem+'/__init__.py']:
                if name in files and name not in seen:queue.append(name)
    while queue:
        name=queue.pop()
        if name in seen:continue
        seen.add(name)
        for node in ast.walk(ast.parse(files[name].read_text())):
            if isinstance(node,ast.Import):
                for a in node.names:add(a.name)
            elif isinstance(node,ast.ImportFrom):
                prefix='.'.join(Path(name).parts[:-node.level]) if node.level else ''
                module=(prefix+'.' if prefix else '')+(node.module or '')
                add(module)
                for a in node.names:add(module+'.'+a.name)
            elif isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.endswith('.py'):
                for candidate in [node.value,(Path(name).parent/node.value).as_posix()]:
                    if candidate in files and candidate not in seen:queue.append(candidate)
    return {'description':'Maintained forecast Python dependency closure; generated studies and models excluded.',
            'files':{name:hashlib.sha256(files[name].read_bytes()).hexdigest() for name in sorted(seen)}}


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--write',action='store_true');g.add_argument('--check',action='store_true')
    a=p.parse_args();project=Path(__file__).resolve().parents[1];path=project/'docs/FORECAST_SOURCE_MANIFEST.json';actual=build(project)
    if a.write:path.write_text(json.dumps(actual,indent=2)+'\n')
    elif json.loads(path.read_text())['files']!=actual['files']:raise SystemExit('Forecast dependency manifest is stale; regenerate after reviewing source changes.')
    print(f"Forecast dependency manifest: {len(actual['files'])} Python files verified.")


if __name__=='__main__':main()
