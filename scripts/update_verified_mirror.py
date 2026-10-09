"""Future mirror updater: fixed official TLS source, strict checks, no corrections."""
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

OFFICIAL='https://www.cftc.gov/dea/newcot/FinFutWk.txt'
MARKETS={
 'AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE','BRITISH POUND - CHICAGO MERCANTILE EXCHANGE',
 'CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE','EURO FX - CHICAGO MERCANTILE EXCHANGE',
 'JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE','NZ DOLLAR - CHICAGO MERCANTILE EXCHANGE',
 'SWISS FRANC - CHICAGO MERCANTILE EXCHANGE','BRAZILIAN REAL - CHICAGO MERCANTILE EXCHANGE',
 'MEXICAN PESO - CHICAGO MERCANTILE EXCHANGE','SO AFRICAN RAND - CHICAGO MERCANTILE EXCHANGE'}
MAX_BYTES=2*1024*1024


def validate(raw,today,*,require_fresh=True):
    if not raw or len(raw)>MAX_BYTES: raise ValueError('Empty/oversized report')
    rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig',errors='strict')),strict=True))
    dates,seen,tracked=set(),set(),[]
    for row in rows:
        if not row: continue
        market=row[0].strip()
        if len(row)!=87 or market in seen: raise ValueError('Malformed/duplicate row')
        seen.add(market)
        report=date.fromisoformat(row[2].strip())
        if report.isoformat()!=row[2].strip() or report.weekday()!=1 or report>today:
            raise ValueError('Invalid report date')
        if require_fresh and not 3 <= (today-report).days <= 10:
            raise ValueError('Invalid or premature report date')
        dates.add(report)
        if market in MARKETS:
            tracked.append(row)
            numeric_indices=[7,8,9,11,12,14,15,17,18,22,23,24,25,26,28,29,31,32,34,35,39,40,42,43,45,46,48,49,51,52,56,57]
            values={i:float(row[i].strip()) for i in numeric_indices}
            if any(not math.isfinite(v) for v in values.values()) or values[7]<=0: raise ValueError('Invalid numeric field')
            for pos,pct in [(8,42),(9,43),(11,45),(12,46),(14,48),(15,49),(17,51),(18,52),(22,56),(23,57)]:
                if values[pos]<0 or values[pos]>values[7] or values[pos]!=int(values[pos]) or not 0<=values[pct]<=100 or abs(values[pct]-values[pos]/values[7]*100)>0.11:
                    raise ValueError('Anomalous positions/percentage')
    if len(dates)!=1 or len(tracked)!=10 or {r[0].strip() for r in tracked}!=MARKETS: raise ValueError('Incomplete report')
    return next(iter(dates)),{r[0].strip():r for r in tracked}


def decision(raw,previous,today):
    current,rows=validate(raw,today)
    if not previous: raise ValueError('A verified existing mirror baseline is required')
    # Accepted history ages during publication delays; validate its contents
    # without applying the incoming delivery's freshness window.
    old,oldrows=validate(previous,today,require_fresh=False)
    if current==old:
        if rows!=oldrows: raise ValueError('Correction to existing report requires review')
        return False
    if (current-old).days!=7: raise ValueError('Stale or skipped report; recover official archives first')
    return True


def fetch(sleep=time.sleep):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args): return None
    for attempt in range(3):
        try:
            req=urllib.request.Request(OFFICIAL,headers={'User-Agent':'Mozilla/5.0 Forex-COT-Mirror'})
            with urllib.request.build_opener(NoRedirect).open(req,timeout=60) as response:
                raw=response.read(MAX_BYTES+1)
                if response.status!=200 or len(raw)>MAX_BYTES: raise ValueError('Unexpected/oversized response')
                return raw
        except (urllib.error.URLError,TimeoutError):
            if attempt==2: raise ValueError('Official source unavailable after retries') from None
            sleep(10*(attempt+1))


def main():
    raw=fetch()
    previous=Path('FinFutWk.txt').read_bytes()
    today=datetime.now(timezone.utc).date()
    changed=decision(raw,previous,today)
    if changed:
        temporary=Path('FinFutWk.tmp')
        temporary.write_bytes(raw)
        os.replace(temporary,'FinFutWk.txt')
        report,_=validate(raw,today)
        Path('verification.json').write_text(json.dumps({'source':OFFICIAL,'report_date':report.isoformat(),
            'sha256':hashlib.sha256(raw).hexdigest(),'source_run_id':os.environ['GITHUB_RUN_ID']},sort_keys=True)+'\n')
    with open(os.environ['GITHUB_OUTPUT'],'a') as f: f.write(f"changed={'true' if changed else 'false'}\n")
    print('New validated official report.' if changed else 'Same verified report; nothing changed.')


if __name__=='__main__':
    try: main()
    except Exception: raise SystemExit('Mirror validation failed; previous official delivery preserved. Retry source delays; review gaps/corrections/anomalies.') from None
