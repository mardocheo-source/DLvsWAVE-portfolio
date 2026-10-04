"""Compact feature-width and sequential-worker contracts; no forecast fitting."""
import json,os,sys,time,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
P=Path(__file__).resolve().parents[1];sys.path[:0]=[str(P/'src'),str(P)]
import pandas as pd
import production_energy as energy
from forecast_search_policy import validate
from run_global_recursive_forecast import workers

class CompactSearch(unittest.TestCase):
    def test_refinement_respects_family_feature_limits(self):
        c=json.loads((P/'configs/japan_compact_bitwise_policy.json').read_text());validate(c)
        frames={'training':pd.DataFrame({'date':['2000-01-01']*20,'event_target':[1]*20})}
        for family in energy.FAMILIES:
            feats=[('packed_' if family=='lcs' else 'astro_')+str(i) for i in range(80)]
            parent={'configuration':energy.propose(1,family,frames,feats,c)}
            for tid in range(2,32):
                candidate=energy.propose(tid,family,frames,feats,c,parent)
                self.assertLessEqual(len(candidate['features']),max(c['energy_feature_counts'][family]))
                self.assertEqual(len(set(candidate['features'])),len(candidate['features']))
    def test_bad_policy_is_rejected(self):
        for c in [{'energy_feature_counts':{'lcs':[0]}},{'max_parallel_workers':0},{'astronomy_shift_max_base_fields':-1}]:
            with self.assertRaises(ValueError):validate(c)
    def test_workers_do_not_overlap(self):
        sleep=time.sleep
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);program=root/'worker.py'
            program.write_text('import sys,time,json\nfrom pathlib import Path\ns=time.time();time.sleep(.05);Path(sys.argv[1]).write_text(json.dumps([s,time.time()]))\n')
            jobs=[([program,root/f'{i}.json'],root/f'{i}.log') for i in range(2)]
            with patch('run_global_recursive_forecast.time.sleep',lambda _:sleep(.02)):
                workers(jobs,time.time()+10,{'max_parallel_workers':1,'minimum_available_memory_mb':1})
            a,b=[json.loads((root/f'{i}.json').read_text()) for i in range(2)]
            self.assertLessEqual(a[1],b[0])
    def test_japan_initialization_freezes_maintained_closure(self):
        from run_causal_japan_energy import initialize
        from forecast_source_manifest import build
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'japan'
            initialize({'location_reference_root':'not-used-during-initialization'},root)
            expected=set(build(P)['files'])
            actual={str(p.relative_to(root/'source_snapshot/src')) for p in (root/'source_snapshot/src').rglob('*.py')}
            self.assertEqual(expected,actual)
            self.assertIn('DLVS_PYTHON',(root/'commands/run_causal_energy.sh').read_text())
