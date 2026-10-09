# Proposed mirror retries — inactive template

`deploy/automation/update-cftc.yml` is not an active Actions workflow. This draft
does not replace/activate the existing Saturday workflow, configure credentials,
fetch/push real reports or dispatch publishing. After review, the owner can
replace `.github/workflows/test-cftc.yml` with this template; do not keep two
scheduled mirror writers.

Proposed checks: Friday 21:23/23:23 UTC and 01:23/07:23/13:23/19:23 UTC
Saturday–Tuesday. They follow the normal CFTC 15:30 Eastern release and cover
Monday holiday delays. Source checks 24 minutes later. See the
[official release schedule](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm).
GitHub scheduling is best effort; public schedules may pause after inactivity.

The updater uses only the fixed official CFTC TFF Futures-Only HTTPS endpoint,
bounded retries/timeouts, no redirects and a size cap. It checks 87 fields, one
canonical Tuesday date aged 3–10 days, ten distinct markets, finite values,
positive open interest, integral/nonnegative positions and consistent percentages.
Identical tracked reports are no-ops. Changed existing reports, backward dates,
skipped weeks and incomplete/anomalous reports fail for explicit review. Commit
history retains previous deliveries; concurrency and fast-forward pushes prevent
lost writes. Verification metadata contains official URL/date/hash/run ID only.

The private source independently compares pinned mirror bytes to a direct
official download, then validates every weekly change against immutable history.
A mirror manifest alone is not sufficient authentication. No website token or
paid service is needed here. Only repository-scoped `GITHUB_TOKEN` Contents write
is used. Main rules must allow the reviewed report-only bot update; no broad PAT,
Workflows/Admin permission or protection bypass on application repositories is
needed. Review these data-branch/rule permissions once before activation.

After the three draft PRs are reviewed, enable owner Actions failure notifications,
replace the workflow in a separate approved activation change, configure
source/site as their guides specify, and check the first complete release.
Failed validation preserves the previous report. Safe Actions annotations report
delivery delays/gaps/corrections/permissions without data dumps. Missing or
corrected records require reviewed official archive recovery; never silently
rewrite verified history. Tests are synthetic and never publish reports.
