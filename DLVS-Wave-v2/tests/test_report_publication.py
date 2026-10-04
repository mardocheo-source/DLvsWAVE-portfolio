"""Report placement and preservation tests, without PDF rendering or model imports."""
from pathlib import Path
import json,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from forecast_report_publication import publish_edition

class ReportPublication(unittest.TestCase):
    def test_root_and_branch_reports_archive_previous_and_are_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            study=Path(tmp)/'study';edition=study/'report_editions/new';edition.mkdir(parents=True)
            (study/'01_energy_forecast_m77').mkdir();(study/'02a_spatial_zones_forecast_multitarget').mkdir()
            names=['JOINT_ENERGY_AND_SPACE_SUPER_CONSOLIDATED_REPORT.pdf','ENERGY_FORECAST_MASTER_REPORT.pdf','SPATIAL_ZONES_MASTER_REPORT.pdf']
            for name in names:(edition/name).write_bytes(b'%PDF-new')
            (study/names[0]).write_bytes(b'%PDF-original')
            (edition/'publication_manifest.json').write_text(json.dumps({'source_study':str(study),'status':'reviewed','joint_navigation':{'pages':42}}))
            result=publish_edition(study,edition)
            self.assertEqual(result,study/names[0])
            for name in names:self.assertEqual((study/name).read_bytes(),b'%PDF-new')
            archives=list((study/'report_editions').glob('previous_*'));self.assertEqual(len(archives),1)
            self.assertEqual((archives[0]/names[0]).read_bytes(),b'%PDF-original')
            self.assertEqual((study/'01_energy_forecast_m77'/names[1]).read_bytes(),b'%PDF-new')
            publish_edition(study,edition)
            self.assertEqual(len(list((study/'report_editions').glob('previous_*'))),1)
    def test_wrong_study_is_rejected_before_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            study=Path(tmp);edition=study/'edition';edition.mkdir()
            (edition/'publication_manifest.json').write_text(json.dumps({'source_study':'/another/study'}))
            with self.assertRaises(ValueError):publish_edition(study,edition)
            self.assertFalse((study/'REPORTS.md').exists())
