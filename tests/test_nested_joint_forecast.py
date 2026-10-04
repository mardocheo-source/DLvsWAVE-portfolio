import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "DLVS-Wave-v2/src"), str(ROOT / "DLVS-Wave-v2")]
from uncompressed_pipeline.nested_data import normalize_catalog, select_validation, scope_catalog, unit_vectors, fit_spherical_zones
from uncompressed_pipeline.nested_models import make_spatial_frame, make_energy_frame, inner_boundary
from uncompressed_pipeline.intensity_magnitude_spectrum import reference_potential_spectrum
from uncompressed_pipeline.nested_reference_fusion import fit_reference_fusion, apply_reference_fusion
from run_nested_joint_forecast import select_children, enqueue_saved_children


class NestedJointContracts(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "master/nested_joint_config.json").read_text())

    def catalog(self, recent_mag=7.5):
        dates = list(pd.date_range("1950-01-02", periods=60, freq="360D")) + [pd.Timestamp("2026-01-05"), pd.Timestamp("2026-05-04"), pd.Timestamp("2026-07-06")]
        frame = pd.DataFrame({"id": [str(i) for i in range(len(dates))], "time": dates,
                              "latitude": 35., "longitude": 140., "mag": [7.8] * 60 + [recent_mag] * 3})
        return normalize_catalog(frame, self.config)

    def test_bounded_threshold_reduction_supplies_recent_energy_events(self):
        split = select_validation(self.catalog(), self.config, "energy")
        self.assertEqual(split["status"], "sufficient")
        self.assertAlmostEqual(split["threshold"], 7.5)
        self.assertEqual(split["validation_event_slots"], 3)
        self.assertLessEqual(split["months"], 36)
        self.assertEqual(split["initial_threshold"], 7.7)

    def test_old_events_never_force_ten_year_validation(self):
        frame = self.catalog(7.0)
        split = select_validation(frame, self.config, "energy")
        self.assertEqual(split["status"], "insufficient_data")
        self.assertTrue(all(row["months"] <= 36 for row in split["audit"]))
        self.assertTrue(all(row["threshold"] >= 7.4 for row in split["audit"]))

    def test_training_retention_is_enforced(self):
        events = self.catalog(7.8).tail(6)
        self.assertEqual(select_validation(events, self.config, "energy")["status"], "insufficient_data")

    def test_same_slot_events_do_not_inflate_temporal_count(self):
        frame = self.catalog()
        last = frame.tail(3).copy()
        last["time"] = pd.to_datetime(["2026-07-06", "2026-07-07", "2026-07-08"])
        combined = normalize_catalog(pd.concat([frame.iloc[:-3], last]), self.config)
        self.assertEqual(select_validation(combined, self.config, "energy")["status"], "insufficient_data")

    def test_antimeridian_membership_and_deduplication(self):
        frame = pd.DataFrame({"id": ["a", "b", "a", "future"], "time": ["2026-01-01"] * 3 + ["2030-01-01"],
                              "mag": 7., "latitude": 0., "longitude": [179, -179, 179, 0]})
        clean = normalize_catalog(frame, self.config)
        self.assertEqual(len(clean), 2)
        centers = unit_vectors(np.array([0, 0]), np.array([180, 0])).tolist()
        selected = scope_catalog(clean, [{"centers": centers, "zone": 0}])
        self.assertEqual(set(selected.id), {"a", "b"})

    def test_event_only_spatial_frame_retains_multiple_events(self):
        frame = self.catalog(7.8)
        split = select_validation(frame, self.config, "energy")
        extra = frame.tail(1).copy(); extra["id"] = "extra"; extra["time"] += pd.Timedelta(days=1)
        frame = normalize_catalog(pd.concat([frame, extra]), self.config)
        dates = pd.date_range("1900-01-01", "2026-12-07", freq="7D")
        astro = pd.DataFrame({"date": dates, "astro_x": np.arange(len(dates))})
        zones = {"centers": unit_vectors(np.array([35, -35]), np.array([140, -40])).tolist(), "count": 2}
        master = make_spatial_frame(astro, frame, split, zones, self.config)
        history = master.loc[master.role != "forecast"]
        self.assertEqual(len(history), len(frame))
        self.assertTrue(history.id.notna().all())
        self.assertEqual(history.loc[history.id == "extra", "role"].iloc[0], "validation")
        self.assertTrue(master.loc[master.role == "forecast", "target"].isna().all())

    def test_energy_keeps_quiet_slots_and_excludes_partial_current_slot(self):
        events = self.catalog(7.8)
        split = select_validation(events, self.config, "energy")
        dates = pd.date_range("1900-01-01", "2026-12-07", freq="7D")
        astro = pd.DataFrame({"date": dates, "astro_x": 0.})
        master = make_energy_frame(astro, events, split, self.config)
        self.assertTrue((master.loc[master.role == "validation", "target"] == 0).any())
        self.assertFalse(master.date.eq(pd.Timestamp("2026-08-31")).any())
        self.assertTrue((master.loc[master.role == "training", "date"] < pd.Timestamp(split["validation_start"])).all())

    def test_counts_can_exceed_three(self):
        config = copy.deepcopy(self.config)
        config["energy"].update({"desired_events": 6, "minimum_events": 5})
        events = self.catalog(7.8)
        extra = events.tail(3).copy(); extra["id"] = extra.id + "_extra"; extra["time"] -= pd.Timedelta(days=21)
        clean = normalize_catalog(pd.concat([events, extra]), config)
        split = select_validation(clean, config, "energy")
        self.assertEqual(split["status"], "sufficient")
        self.assertGreaterEqual(split["validation_event_slots"], 6)

    def test_reference_potential_transfer_is_unchanged(self):
        p1=np.array([0.,.02,.4]); p2=np.array([0.,.1,.6]); p3=np.array([0.,.1,.7])
        s=np.clip(.4*np.minimum(1,p1*3.8)+.3*p2+.3*p3/.7,0,1)
        expected=np.round(np.where(s<.02,4.9,4.9+3.25*s**.6),2)
        actual,mag=reference_potential_spectrum(p1,p2,p3)
        np.testing.assert_allclose(actual,s); np.testing.assert_array_equal(mag,expected)

    def test_reference_fusion_accepts_more_than_two_events(self):
        y=np.array([0,1,0,0,1,0,0,1,0,0])
        bank=np.stack([np.where(y==1,.8,.02),np.where(y==1,.65,.03)])
        spec=fit_reference_fusion(y,bank)
        self.assertEqual(spec['inner_event_count'],3)
        self.assertEqual(apply_reference_fusion(bank,spec).shape,y.shape)

    def test_best_available_continues_despite_low_quality(self):
        config=copy.deepcopy(self.config); config['continuation_policy']='best_available'
        centers=unit_vectors(np.array([0,0]),np.array([0,180])).tolist()
        node={'level':0,'path':[],'geometry':{'area_fraction':1.},'zones':{'count':2,'centers':centers}}
        dates=pd.to_datetime(['2026-09-07','2026-09-14'])
        results={'energy':{'summary':{'metrics':{'recall':0.,'false_alarm_fraction':.5}},'forecast':pd.DataFrame({'date':dates,'score':[.1,.2]})},
                 'location':{'summary':{'metrics':{'represented_zones':2,'skill_over_majority':-.2,'median_centroid_distance_km':19000.}},
                 'forecast':pd.DataFrame({'date':dates,'zone_score_0':[.4,.7],'zone_score_1':[.6,.3]})}}
        selection,children=select_children(node,results,config)
        self.assertEqual(selection['selected_zones'],[0])
        self.assertGreater(len(selection['quality_notes']),0)
        self.assertEqual(len(children),1)

    def test_resume_queue_recovers_reported_child_without_duplication(self):
        centers=unit_vectors(np.array([0,0]),np.array([0,180])).tolist()
        child={'zone':1,'path':[{'centers':centers,'zone':1}],'geometry':{'area_fraction':.5}}
        parent={'id':'root','level':0,'status':'completed','report':'report.pdf','selection':{'selected_zones':[1],'candidates':[child]}}
        state={'nodes':[parent]}
        enqueue_saved_children(state,self.config); enqueue_saved_children(state,self.config)
        self.assertEqual(len(state['nodes']),2)
        self.assertEqual(state['nodes'][1]['level'],1)


if __name__ == "__main__": unittest.main()
