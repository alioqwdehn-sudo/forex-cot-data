import csv
from datetime import date
import io
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import update_verified_mirror as mirror


def fixture(day='2026-09-29'):
    output=io.StringIO();writer=csv.writer(output)
    for market in sorted(mirror.MARKETS):
        row=['0']*87;row[0],row[2],row[7]=market,day,'1000'
        for pos,pct in [(8,42),(9,43),(11,45),(12,46),(14,48),(15,49),(17,51),(18,52),(22,56),(23,57)]:row[pos],row[pct]='100','10'
        writer.writerow(row)
    return output.getvalue().encode()


class MirrorTests(unittest.TestCase):
    def test_new_and_duplicate(self):
        raw=fixture();today=date(2026,10,9)
        self.assertFalse(mirror.decision(raw,raw,today))
        self.assertTrue(mirror.decision(fixture('2026-10-06'),raw,today))
    def test_gap_future_and_stale_rejected(self):
        for new,old,today in [('2026-10-13','2026-09-29',date(2026,10,16)),('2026-10-13','2026-10-06',date(2026,10,9)),('2026-09-29','2026-10-06',date(2026,10,9))]:
            with self.assertRaises(ValueError):mirror.decision(fixture(new),fixture(old),today)
    def test_partial_duplicate_numeric_and_pct_rejected(self):
        lines=fixture().splitlines(keepends=True)
        for raw in [b''.join(lines[:-1]),b''.join(lines+[lines[0]]),fixture().replace(b',1000,',b',nan,',1),fixture().replace(b',10,',b',99,',1)]:
            with self.assertRaises(ValueError):mirror.validate(raw,date(2026,10,9))
    def test_correction_rejected(self):
        with self.assertRaises(ValueError):mirror.decision(fixture().replace(b',100,',b',101,',1),fixture(),date(2026,10,9))
    def test_template_inactive(self):
        root=Path(__file__).resolve().parents[1]
        self.assertTrue((root/'deploy/automation/update-cftc.yml').exists())
        self.assertNotIn('23 21,23',(root/'.github/workflows/test-cftc.yml').read_text())


if __name__=='__main__':unittest.main()
