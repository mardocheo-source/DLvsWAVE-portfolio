"""Offline contract tests. All generated data are synthetic and temporary.

Run: python -m unittest discover -s DLVS-Wave-v2/tests -v
These tests verify automation and arithmetic, not earthquake prediction skill.
"""
from pathlib import Path
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT/'src'), str(PROJECT)]
os.environ.setdefault('MPLCONFIGDIR', '/tmp/dlvs-forecast-test-matplotlib')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')

import numpy as np
import pandas as pd
from forecast_cli import validate, source_hashes
from production_geography import membership, select_peak, energy_contract, prepare_location
from world_weighted_energy_fusion import choose, STAGES, BRANCHES
from world_zoom import temporal_zoom, event_rectangle
from world_zone_reconciliation import decide, apply


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


class ForecastContracts(unittest.TestCase):
    def config(self):
        return json.loads((PROJECT/'configs/world_nested_production.json').read_text())

    def test_examples_are_portable_and_valid(self):
        for name in ['world_nested_production', 'region_single_example', 'region_nested_example', 'world_nested_astro_refit']:
            c=json.loads((PROJECT/'configs'/f'{name}.json').read_text());validate(c)
            self.assertNotIn('/mnt/', json.dumps(c))

    def test_astro_origin_protocol_and_actual_model_isolation(self):
        from world_origin_energy import prepare, audit, PROTOCOL
        c=self.config();c.update(energy_protocol=PROTOCOL,infill_seed_mode='pi_pairs',terminal_infill='all_observed',training_start='1970-01-01')
        validate(c)
        dates=pd.to_datetime([f'{y}-01-03' for y in range(1970,2020,2)]+['2025-06-02','2026-03-02','2026-07-28'])
        events=pd.DataFrame({'time':dates,'date':dates.to_period('W-SUN').start_time,'mag':[7.8]*len(dates),'id':np.arange(len(dates))})
        grid=pd.date_range('1970-01-05','2027-01-31',freq='7D')
        astro=pd.DataFrame({'date':grid,**{f'astro_body{i}_ra':np.sin(np.arange(len(grid))/(10+i)) for i in range(9)}})
        # Deliberately supplied seismic columns must never reach the new masters.
        astro['seis_future']=123.;inputs={b:astro for b in c['branches']}
        with tempfile.TemporaryDirectory() as t:
            root,contract=prepare(events,inputs,Path(t)/'one',c)
            result=audit(c,root,root/'test_audit.json',exercise_models=True)
            self.assertEqual(result['status'],'passed')
            data=root/'main_bodies_branch/01_data'
            first=pd.read_csv(data/'validation_1/training.csv');future=pd.read_csv(data/'forecast/training.csv')
            self.assertGreater(future.event_target.sum(),first.event_target.sum())
            self.assertTrue(future.date.max().startswith('2026-07-27'))
            self.assertLess(future.observed_target_days.iloc[-1],7)
            self.assertNotIn('seis_future',future)
            # Future observations cannot affect contracts, labels or codebooks.
            later=pd.DataFrame({'time':[pd.Timestamp('2028-01-01')],'date':[pd.Timestamp('2027-12-27')],'mag':[9.9],'id':['future']})
            r2,_=prepare(pd.concat([events,later]),inputs,Path(t)/'two',c)
            for f in data.rglob('*.csv'):
                self.assertEqual(f.read_bytes(),(r2/'main_bodies_branch/01_data'/f.relative_to(data)).read_bytes())
            # Astronomical prediction values do not fit validation quantile edges.
            changed=astro.copy();changed.loc[changed.date>=pd.Timestamp(contract['training_end_exclusive']),changed.columns.str.startswith('astro_')]+=1000
            r3,_=prepare(events,{b:changed for b in c['branches']},Path(t)/'three',c)
            self.assertEqual((data/'validation_1/bitwise_codebook.json').read_bytes(),(r3/'main_bodies_branch/01_data/validation_1/bitwise_codebook.json').read_bytes())

    def test_magnitude_cli_overrides_are_saved_without_touching_config(self):
        with tempfile.TemporaryDirectory() as t:
            study=Path(t)/'study';config=PROJECT/'configs/world_nested_production.json';before=config.read_bytes()
            args=['--energy-training-magnitude','7.7','--energy-validation-magnitude','7.5','--energy-validation-min-magnitude','7.5','--location-training-magnitude','6.8','--location-validation-magnitude','6.4','--location-validation-min-magnitude','6.4']
            subprocess.run([sys.executable,str(PROJECT/'src/forecast_cli.py'),'run','--config',str(config),'--output',str(study),'--initialize-only',*args],check=True,capture_output=True)
            saved=json.loads((study/'run_configuration.json').read_text())
            self.assertEqual(saved['energy_training_magnitude'],7.7);self.assertEqual(saved['energy_validation_magnitude'],7.5)
            self.assertEqual(saved['location_training_magnitude'],6.8);self.assertEqual(saved['location_validation_magnitude'],6.4)
            self.assertEqual(config.read_bytes(),before)
        for change in [{'location_validation_min_magnitude':5.0},{'energy_validation_min_magnitude':8.0},{'energy_training_magnitude':float('nan')}]:
            with self.assertRaises(ValueError):validate({**self.config(),**change})

    def test_independent_energy_thresholds_reach_training_and_refit_labels(self):
        from world_origin_energy import prepare
        c=self.config();c.update(energy_protocol='origin_refit_astro_only',training_start='1970-01-01',energy_training_magnitude=7.7,energy_validation_magnitude=7.1,energy_validation_min_magnitude=7.1)
        times=pd.to_datetime([f'{y}-01-03' for y in range(1970,2020,2)]+['2022-09-05','2023-03-27'])
        e=pd.DataFrame({'time':times,'date':times.to_period('W-SUN').start_time,'mag':[7.8]*25+[7.1,7.1],'id':np.arange(27)})
        grid=pd.date_range('1970-01-05','2027-01-31',freq='7D');astro=pd.DataFrame({'date':grid,'astro_test':np.sin(np.arange(len(grid)))})
        with tempfile.TemporaryDirectory() as t:
            root,contract=prepare(e,{b:astro for b in BRANCHES},Path(t),c)
            self.assertEqual(contract['training_magnitude'],7.7);self.assertEqual(contract['effective_magnitude'],7.1)
            data=root/BRANCHES[0]/'01_data'
            tr=pd.read_csv(data/'forecast/training.csv');val=pd.read_csv(data/'validation_master.csv')
            self.assertEqual(val.event_target.sum(),2)
            for date in ['2022-09-05','2023-03-27']:
                self.assertEqual(tr.loc[tr.date.str.startswith(date),'event_target'].iloc[0],0)
            with self.assertRaises(ValueError):prepare(e,{b:astro for b in BRANCHES},Path(t)/'strict',{**c,'energy_validation_magnitude':7.7,'energy_validation_min_magnitude':7.7})

    def test_wrong_protocol_and_dates_rejected(self):
        for change in [{'infill_seed_mode':'pi_pairs'}, {'catalog_cutoff':'2026-09-01'}, {'energy_validation_events':30}, {'main_fusion_weight':1.5}]:
            with self.assertRaises(ValueError): validate({**self.config(), **change})

    def test_date_line_rectangle_and_union_without_single_zone(self):
        e=pd.DataFrame({'latitude':[0,0,0], 'longitude':[175,-175,0]})
        np.testing.assert_array_equal(membership(e,[{'type':'rectangle','bounds':[-10,10,170,190]}]),[True,True,False])
        np.testing.assert_array_equal(membership(e,[{'centers':[[1,0,0],[-1,0,0]],'zones':[0,1]}]),[True]*3)

    def test_first_event_not_largest_and_flat_has_none(self):
        c={'selection_mode':'first_event','forecast_start':'2026-10-19'}
        f=pd.DataFrame({'date':pd.date_range('2026-10-19',periods=5,freq='7D'),'predicted_prob':[.001,.005,.001,.02,.001]})
        self.assertEqual(select_peak(f,c)['selected']['apex'],'2026-10-26')
        f.predicted_prob=.001;self.assertIsNone(select_peak(f,c)['selected'])

    def test_temporal_zoom(self):
        z=temporal_zoom({'child_weeks_before':2,'child_weeks_after':2},{'apex':'2026-11-02'})
        self.assertEqual(z,{'forecast_start':'2026-10-19','forecast_end':'2026-11-22','selection_start':'2026-10-19'})

    def test_recent_rectangle_excludes_post_cutoff_observations(self):
        e=pd.DataFrame({'time':pd.to_datetime(['2025-01-01']*4+['2028-01-01']),'latitude':[-10,-9,-8,-7,60],'longitude':[175,178,-179,-176,0],'mag':[7]*5,'id':list('abcde')})
        rules=[{'type':'rectangle','bounds':[-90,90,120,220]}]
        c={'catalog_cutoff':'2026-07-31Z'.replace('31Z','31T00:00:00Z'),'child_rectangle_min_events':3}
        r,a=event_rectangle(e,rules,c)
        self.assertEqual(a['support_events'],4);self.assertNotIn('e',a['event_ids'])
        self.assertLess(r[-1]['bounds'][3]-r[-1]['bounds'][2],30)

    def make_stages(self, root):
        for branch in BRANCHES:
            for i,stage in enumerate(STAGES):
                p=root/branch/stage;p.mkdir(parents=True)
                probabilities=[.1,.9,.1] if branch==BRANCHES[0] else [.2,.4,.2]
                if i==2:probabilities=[.001]*3
                for split in ['validation_predictions','prospective_forecast']:
                    f=pd.DataFrame({'date':['2026-10-19','2026-10-26','2026-11-02'],'predicted_prob':probabilities})
                    if split=='validation_predictions':f['event_target']=[0,1,0];f['relative_week']=[-1,0,1];f['event_number']=1
                    f.to_csv(p/f'{split}.csv',index=False)
                put(p/'fusion_manifest.json',{'validation_metrics':{'val_centered_peak_count':2 if i==2 else 1,'val_false_positives':0,'calibration_objective_on_final_clipped_curve':3-i}})

    def test_weighted_hunt_preserves_sources_and_aligns_both_splits(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);self.make_stages(root)
            original={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*.csv')}
            _,a=choose(root,{'huntanyway':False});self.assertEqual(a['fused_peak_dates'],[])
            for weight in [.85,0,1]:
                _,a=choose(root,{'huntanyway':True,'main_fusion_weight':weight,'parent_event':{'start':'2026-11-02','end':'2026-11-08'}})
                self.assertTrue(a['recovery_uses_forecast_curve_shape'])
                for split in ['validation_predictions','prospective_forecast']:
                    f=pd.read_csv(root/'fusion_main_minor'/f'final_{split}.csv')
                    np.testing.assert_allclose(f.predicted_prob,weight*np.array([.1,.9,.1])+(1-weight)*np.array([.2,.4,.2]),atol=1e-15)
            self.assertEqual(original,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in original})

    def test_misaligned_fusion_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);self.make_stages(root)
            p=root/BRANCHES[1]/STAGES[2]/'prospective_forecast.csv'
            f=pd.read_csv(p);f.loc[0,'date']='2026-10-18';f.to_csv(p,index=False)
            with self.assertRaises(ValueError):choose(root,{})

    def test_energy_threshold_contract_keeps_recent_validation_out_of_training(self):
        dates=pd.to_datetime([f'{y}-01-03' for y in range(1970,2020,2)]+['2022-09-05','2023-03-27'])
        e=pd.DataFrame({'time':dates,'date':dates.to_period('W-SUN').start_time,'mag':[7.5]*25+[7.1,7.1],'id':np.arange(27)})
        c=self.config();c.update(energy_magnitude=7.7,maximum_energy_target_reduction=.6)
        contract,val=energy_contract(e,c)
        self.assertAlmostEqual(contract['effective_magnitude'],7.1)
        self.assertEqual(val.event_target.sum(),2)
        self.assertTrue((val.date>=pd.Timestamp(contract['training_end_exclusive'])).all())
        with self.assertRaises(ValueError):energy_contract(e,{**c,'maximum_energy_target_reduction':.5})

    def test_location_has_only_event_rows_and_training_only_zone_fit(self):
        with tempfile.TemporaryDirectory() as t:
            dates=pd.date_range('2010-01-04',periods=60,freq='28D').append(pd.date_range('2025-01-06',periods=8,freq='28D'))
            e=pd.DataFrame({'time':dates,'date':dates,'mag':7.,'id':np.arange(len(dates)),'latitude':np.where(np.arange(len(dates))%2,35,-20),'longitude':np.where(np.arange(len(dates))%2,140,170)})
            grid=pd.date_range('2010-01-04','2027-01-25',freq='7D');astro=pd.DataFrame({'date':grid,'astro_test':np.sin(np.arange(len(grid)))})
            c=self.config();c.update(zone_counts=[2],minimum_zone_training_events=3,minimum_location_training_events=6,minimum_location_validation_events=4,location_validation_days=730)
            root,m,z=prepare_location(e,{b:astro for b in BRANCHES},Path(t),c)
            f=pd.read_csv(root/BRANCHES[0]/'01_data/training_master.csv')
            self.assertTrue((f.event_count>0).all());self.assertTrue((f[['target_Zone_0','target_Zone_1']].sum(axis=1)>0).all())
            self.assertLess(f.date.max(),m['validation_start']);self.assertEqual(sum(q['training_event_count'] for q in z['zones']),m['training_events'])
            c.update(maximum_location_validation_events=6,compact_location_validation=True)
            _,compact,zc=prepare_location(e,{b:astro for b in BRANCHES},Path(t)/'compact',c)
            self.assertEqual(compact['validation_events'],4)
            self.assertEqual(len(compact['validation_event_counts']),2)
            self.assertGreater(compact['training_events'],m['training_events'])
            self.assertTrue(compact['window_adjustments'])
            # Lower-magnitude observations may enter validation, never training.
            small=e.copy();small['mag']=6.4;small['id']=small.id+1000
            c.update(location_training_magnitude=6.8,location_validation_magnitude=6.4,location_validation_min_magnitude=6.4)
            rr,mm,_=prepare_location(pd.concat([e,small]),{b:astro for b in BRANCHES},Path(t)/'separate',c)
            training_events=pd.read_csv(rr/'01_data/training_events.csv');validation_events=pd.read_csv(rr/'01_data/validation_events.csv')
            self.assertGreaterEqual(training_events.mag.min(),6.8);self.assertEqual(validation_events.mag.min(),6.4)
            self.assertEqual(mm['requested_validation_magnitude'],6.4);self.assertEqual(mm['validation_magnitude'],6.4)


    def test_zone_union_automatic_and_archive_keeps_budget(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);parent=root/'L0/n000';node=root/'L1/n001';node.mkdir(parents=True)
            put(parent/'node_state.json',{'membership_rules':[]})
            put(parent/'02_location_forecast/01_data/spatial_zones_metadata.json',{'centers':[[1,0,0],[0,1,0]]})
            f=parent/'02_location_forecast/dual_method_reports/fused_methods/prospective_forecast.csv';f.parent.mkdir(parents=True)
            pd.DataFrame({'date':['2026-10-26','2026-11-02'],'prob_Zone_0':[.51,.49],'prob_Zone_1':[.49,.51]}).to_csv(f,index=False)
            e=node/'01_energy_forecast/fusion_main_minor/final_prospective_forecast.csv';e.parent.mkdir(parents=True)
            pd.DataFrame({'date':['2026-10-19','2026-10-26','2026-11-02'],'predicted_prob':[.1,.8,.1]}).to_csv(e,index=False)
            events=pd.DataFrame({'time':pd.to_datetime(['2025-01-01']*4),'latitude':[0,1,2,3],'longitude':[20,30,60,70],'mag':[7]*4,'id':list('abcd')})
            c={**self.config(),'parent_event':{'apex':'2026-11-02','start':'2026-11-02','end':'2026-11-08'},'child_rectangle_min_events':3}
            decision=decide(parent,node,events,c);self.assertTrue(decision['triggered']);self.assertEqual(decision['zone_ids'],[0,1])
            entry={'level':1,'node_id':'n001','node_elapsed_seconds':123.,'node_budget_started_epoch':1.}
            apply(root,node,entry,decision);self.assertEqual(entry['node_elapsed_seconds'],123.);self.assertTrue((root/'test/n001_before_zone_union').exists())
            self.assertEqual(entry['reconciliation_count'],1)

    def test_real_energy_families_and_fusion_on_small_synthetic_fixture(self):
        """Fit the actual three families; never substitute generated predictions."""
        import torch
        from production_energy import fit, fuse
        torch.set_num_threads(1)
        rng=np.random.default_rng(14);features=[f'astro_{i}' for i in range(4)]
        train=pd.DataFrame(rng.random((52,4)),columns=features)
        train['date']=pd.date_range('2000-01-03',periods=52,freq='7D').strftime('%Y-%m-%d');train['event_target']=0;train.loc[[10,30],'event_target']=1
        val=pd.DataFrame(rng.random((6,4)),columns=features)
        val['date']=pd.date_range('2002-01-07',periods=6,freq='7D').strftime('%Y-%m-%d')
        val['event_target']=[0,1,0,0,1,0];val['event_number']=[1,1,1,2,2,2];val['relative_week']=[-1,0,1,-1,0,1]
        future=pd.DataFrame(rng.random((5,4)),columns=features);future['date']=pd.date_range('2003-01-06',periods=5,freq='7D').strftime('%Y-%m-%d')
        frames={'training':train,'validation':val,'prospective':future};records=[]
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            for tid,family in enumerate(['kan','deep_learning','lcs'],1):
                c={'trial_id':tid,'family':family,'seed':14,'features':features,'training_start':'2000-01-01','window_before_steps':1,'window_after_steps':1,'background_infill_ratio':.5,'epochs':2,'params':{'grid_size':3,'spline_order':2,'hidden_dim':8,'num_layers':1,'population_size':12,'learning_rate':.001}}
                pred,q,artifact=fit(c,frames);self.assertTrue(artifact)
                again,_,_=fit(copy.deepcopy(c),frames)
                for split in pred:np.testing.assert_allclose(pred[split],again[split],rtol=0,atol=1e-10)
                path=root/f'trial_{tid}.npz';np.savez(path,**pred)
                records.append({'configuration':c,'metrics':q,'predictions_file':str(path)})
            result=fuse(records,frames,root/'fused',{})
            self.assertTrue(result['selected_trials']);f=pd.read_csv(root/'fused/prospective_forecast.csv')
            self.assertEqual(len(f),5);self.assertTrue(np.isfinite(f.predicted_prob).all())


class StandaloneSmoke(unittest.TestCase):
    def test_offline_frozen_run_inputs_resume_status_report_and_tamper_guard(self):
        """Exercise real loaders and stopped-node PDF generation, with no HTTP."""
        with tempfile.TemporaryDirectory(prefix='dlvs-offline-') as t:
            root=Path(t);cache=root/'cache';raw=root/'astro';raw.mkdir()
            c=json.loads((PROJECT/'configs/region_single_example.json').read_text())
            c.update(training_start='2000-01-01',input_cache_dir=str(cache),astronomy_raw_cache=str(raw),main_bodies=['sun'],minor_bodies=['ceres'])
            event=pd.DataFrame({'id':['synthetic-only'],'time':['2020-01-01'],'date':['2019-12-30'],'latitude':[35.],'longitude':[140.],'depth':[10.],'mag':[6.]})
            p=cache/'catalog/events.csv';p.parent.mkdir(parents=True);event.to_csv(p,index=False)
            put(p.parent/'manifest.json',{'contract':{k:c[k] for k in ['training_start','catalog_cutoff','download_floor']},'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
            for group,name,command in [('main','sun','10'),('minor','ceres','1')]:
                f=raw/f'{name}.csv';grid=pd.date_range('1999-09-27','2027-05-17',freq='7D')
                pd.DataFrame({'date':grid,f'astro_{name}_ra_app_min':np.arange(len(grid),dtype=float)}).to_csv(f,index=False)
                put(raw/f'world_{group}_manifest.json',[{'file':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'request':{'observer':'500@399','body':{'name':name,'command':command,'id_type':None}}}])
            cfg=root/'config.json';put(cfg,c);study=root/'study';cli=PROJECT/'src/forecast_cli.py'
            def invoke(*args):
                return subprocess.run([sys.executable,str(cli),*args],capture_output=True,text=True,timeout=90,env=os.environ.copy())
            first=invoke('run','--config',str(cfg),'--output',str(study),'--inputs-only');self.assertEqual(first.returncode,0,first.stderr)
            self.assertTrue((study/'run.sh').exists());self.assertEqual(json.loads((study/'study_state.json').read_text())['status'],'inputs_complete')
            resumed=invoke('resume','--study',str(study));self.assertEqual(resumed.returncode,75,resumed.stderr)
            state=json.loads((study/'study_state.json').read_text());self.assertEqual(state['nodes'][0]['status'],'stopped')
            self.assertEqual(state['nodes'][0]['node_id'],'n000_region')
            from pypdf import PdfReader
            r=PdfReader(study/'WORLD_NESTED_JOINT_REPORT.pdf');self.assertIn('No energy or location models were trained',r.pages[-1].extract_text())
            status=invoke('status','--study',str(study));self.assertEqual(status.returncode,0);self.assertIn('stopped',status.stdout)
            p=study/'source_snapshot/src/world_zoom.py';p.write_text(p.read_text()+'\n# tampering test\n')
            self.assertNotEqual(invoke('resume','--study',str(study)).returncode,0)


if __name__=='__main__': unittest.main()
