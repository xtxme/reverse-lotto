import unittest
import math
import backtest_image_rules as image
import oos_validation as oos
import define_image_rules as definitions
import build_reports
from pathlib import Path
import tempfile,shutil,json,contextlib,io

class ValidationTests(unittest.TestCase):
    def test_unobserved_future_is_not_a_loss(self):
        r = dict(top3='404', bottom2='55', next=None, next2=None, prev=None, prev2=None)
        for s in image.SPECS:
            with self.subTest(rule=s['test_id']):
                self.assertIsNone(s['target'](r))

    def test_horizon_two_requires_intermediate_round(self):
        r = dict(top3='404', bottom2='55', next=None,
                 next2=dict(top3='444',bottom2='06'),prev=None,prev2=None)
        s = next(s for s in image.SPECS if s['test_id']=='R06-primary')
        self.assertIsNone(s['target'](r))

    def test_uniform_brier_includes_all_classes(self):
        self.assertAlmostEqual(oos.uniform_brier(100), .99, places=12)
        self.assertAlmostEqual(oos.uniform_brier(2), .5, places=12)

    def test_image_eleven_does_not_inherit_skip(self):
        s = next(s for s in image.SPECS if s['test_id']=='R11-primary')
        r = dict(top3='404',bottom2='55',next=dict(top3='123',bottom2='06'),
                 next2=dict(top3='123',bottom2='11'),prev=None,prev2=None)
        self.assertTrue(s['target'](r))

    def test_single_digit_event_uses_both_positions(self):
        s = next(s for s in image.SPECS if s['test_id']=='R12-primary')
        for b in ['18','81','88']:
            self.assertTrue(s['target'](dict(next=dict(bottom2=b),next2=None)))
        self.assertFalse(s['target'](dict(next=dict(bottom2='11'),next2=None)))

    def test_last_deterministic_day_is_included_in_permutation(self):
        rows=[dict(trading_day='d1'),dict(trading_day='d1'),dict(trading_day='d2')]
        p,mean,sd=image.perm_test(rows,[1,0,1],[1,0,1],B=10000)
        self.assertTrue(.46<p<.54)
        self.assertTrue(1.46<mean<1.54)

    def test_dynamic_target_null_shuffles_outcomes_not_trigger_labels(self):
        s=next(s for s in image.SPECS if s['test_id']=='R07-primary')
        rows=[dict(trading_day='d',top3=v,bottom2='00',next=dict(top3=v,bottom2='00'),next2=None) for v in ['111','222']]
        p,mean,sd=image.dynamic_perm_test(rows,[True,True],s,B=10000)
        self.assertTrue(.46<p<.54)
        self.assertTrue(.92<mean<1.08)

    def test_R03_definition_includes_ABA_and_excludes_triples(self):
        self.assertIn('ABA',definitions.GLOSSARY['R03'])
        self.assertIn('ไม่รวมตอง',definitions.GLOSSARY['R03'])

    def test_report_without_optional_captures_never_claims_matches(self):
        original_root,original_out=build_reports.ROOT,build_reports.OUT
        with tempfile.TemporaryDirectory(prefix='work_b_report_test_') as tmp:
            root=Path(tmp);shutil.copytree(original_out,root/'outputs')
            for name in ['DEDUPLICATED_RESULTS.csv','FIRST_SEEN_FORECASTS.csv']:
                shutil.copy2(original_root/name,root/name)
            audit=json.loads((root/'outputs/INPUT_AUDIT.json').read_text())
            audit['capture_comparison_after_exclusions']={}
            audit['capture_statuses']={}
            (root/'outputs/INPUT_AUDIT.json').write_text(json.dumps(audit))
            try:
                build_reports.ROOT=root;build_reports.OUT=root/'outputs'
                with contextlib.redirect_stdout(io.StringIO()):build_reports.main()
                final=(root/'FINAL_INDEPENDENT_REPORT_TH.md').read_text()
                self.assertNotIn('saved captures ตรงกับ LINE7,295ผล',final)
                self.assertIn('ไม่มีไฟล์ capture',final)
            finally:
                build_reports.ROOT=original_root;build_reports.OUT=original_out

if __name__=='__main__':
    unittest.main()
