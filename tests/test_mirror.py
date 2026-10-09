import csv
from datetime import date, timedelta
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

    def test_friday_through_tuesday_retries(self):
        incoming,previous=fixture('2026-10-06'),fixture('2026-09-29')
        for offset in range(5):
            today=date(2026,10,9)+timedelta(days=offset)
            with self.subTest(today=today):
                self.assertTrue(mirror.decision(incoming,previous,today))
                self.assertFalse(mirror.decision(incoming,incoming,today))

    def test_holiday_delayed_publication_and_stale_baseline_recovery(self):
        previous,incoming=fixture('2026-09-29'),fixture('2026-10-06')
        # Monday holiday/Tuesday delivery leaves the previous report 13/14 days old.
        for today in (date(2026,10,12),date(2026,10,13),date(2026,10,16)):
            with self.subTest(today=today):
                self.assertTrue(mirror.decision(incoming,previous,today))

    def test_incoming_freshness_still_required(self):
        for today in (date(2026,10,8),date(2026,10,17)):
            with self.subTest(today=today),self.assertRaises(ValueError):
                mirror.decision(fixture('2026-10-06'),fixture('2026-09-29'),today)

    def test_stale_baseline_cannot_hide_gap_or_backward_report(self):
        for previous in (fixture('2026-09-22'),fixture('2026-10-13')):
            with self.subTest(previous=previous[:80]),self.assertRaises(ValueError):
                mirror.decision(fixture('2026-10-06'),previous,date(2026,10,13))

    def test_stale_baseline_still_strictly_validated(self):
        previous=fixture('2026-09-29')
        lines=previous.splitlines(keepends=True)
        invalid=[b''.join(lines[:-1]),b''.join(lines+[lines[0]]),
                 previous.replace(b',1000,',b',nan,',1),
                 previous.replace(b',10,',b',99,',1),
                 fixture('2026-09-28'),fixture('2026-11-03'),
                 previous.replace(b'2026-09-29',b'20260929'),
                 previous.replace(b'2026-09-29',b'2026-09-22',1),
                 previous.replace(b',100,',b',100.5,',1)]
        for baseline in invalid:
            with self.subTest(baseline=baseline[:80]),self.assertRaises(ValueError):
                mirror.decision(fixture('2026-10-06'),baseline,date(2026,10,13))

    def test_delayed_same_date_corrections_and_mismatched_duplicates_rejected(self):
        original=fixture('2026-10-06')
        # A valid change in a reported change field must still fail duplicate comparison.
        rows=list(csv.reader(io.StringIO(original.decode())))
        rows[0][24]='1'
        output=io.StringIO();csv.writer(output).writerows(rows)
        corrected=output.getvalue().encode()
        for today in (date(2026,10,10),date(2026,10,13)):
            with self.subTest(today=today),self.assertRaises(ValueError):
                mirror.decision(corrected,original,today)


if __name__=='__main__':unittest.main()
