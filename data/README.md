# GridWatch dataset (built from NERC quarterly reports)

Built on 12 October 2026 from the public NERC quarterly reports (nerc.gov.ng, resource category "NERC Reports"). All values are traceable to a named report. Nothing here was invented or estimated.

## Files

| File | What it contains | Coverage |
|---|---|---|
| collapse_events.csv | Each grid collapse with date, type, time, restoration, frequency change, generation loss, source report | 2021-02 to 2026-01 (dated events; NERC reports no collapse in 2026 Q2) |
| collapses_per_quarter.csv | Number of total, partial and unspecified collapses per quarter | 2019 Q1 to 2026 Q2 |
| monthly_grid_nerc.csv | Monthly average upper and lower daily system frequency (Hz) and average hourly generation (MWh/h) | Frequency: 2023-07 to 2026-06. Generation: 2024-01 to 2026-06 |
| kaduna_disco_nerc.csv | Kaduna DisCo performance (offtake, losses, collection, metering, remittance) | 2026 Q1 and Q2 |
| scripts/ | The code used to extract the monthly series from the PDF charts | |

## How the monthly series were extracted and checked

The monthly numbers are printed as labels on charts in the reports. I read them by position and matched each number to its month. Every quarter was then checked against the quarterly average that NERC states in its own text: the day-weighted mean of the three months must match NERC's stated quarterly average (generation within 0.5%, frequency within 0.05 Hz). All 36 frequency months and all 30 generation months passed the check. One report (2024 Q2) had misread generation labels, so those months use the 2024 Q3 report's chart, which matches NERC's stated average.

## What the numbers mean (and don't)

- Monthly frequency values are averages of the daily highest and daily lowest frequency, not live readings. They show how stressed the grid was in a month, not what happened minute by minute.
- NERC publishes only monthly and quarterly data. I did not find hourly or minute-level public data. Where NISO publishes daily reports is still unconfirmed.
- Collapse counts per NERC (events per year): 2019: 11, 2020: 4, 2021: 4, 2022: 5, 2023: 3, 2024: 9, 2025: 2, 2026 (Jan-Jun): 2. The figures "222 collapses (2010-2022)" and "about 12 in 2024" used in earlier drafts do not match these NERC counts and should not be used unless you can source them.

## First check: does monthly stress line up with collapses? (Jul 2023 - Jun 2026, 36 months)

| | Collapse months (12) | Calm months (24) |
|---|---|---|
| Average upper daily frequency | 50.78 Hz | 50.72 Hz |
| Average lower daily frequency | 49.17 Hz | 49.27 Hz |
| Average range (upper - lower) | 1.61 Hz | 1.45 Hz |
| Average hourly generation | 4,159 MWh/h | 4,313 MWh/h |

Correlation between the monthly frequency range and the number of collapses in the month is about 0.30. This is a weak signal from a small sample. Treat it as "collapse months looked somewhat more stressed", not as a working predictor.

## Known gaps and items to verify by hand

1. 2019-2020 reports give counts only, no dates. 2020 Q1 is inconsistent (the 2020 Q1 report says 1 total collapse; the 2020 Q2 report says 2).
2. Times are blank where I did not see them in the text (for example 2021 events, 15 March 2022, 4 February 2024, 6 July 2024).
3. 2022-07-20: the table header says 18:30 but the narrative says 11:27 with restoration at 12:00, so 11:27 is used. Check the report page.
4. 2023 events are listed as "unspecified" type because the table I read does not say total or partial.
5. Seven older PDFs on the NERC site are damaged at the end. I read them with a repair tool. Spot check any figure from those before quoting it.
6. Reports for 2017 Q3-2018 Q4 exist on the NERC site but were not used.

## Sources

NERC quarterly reports, 2019 Q1 to 2026 Q2, available free at nerc.gov.ng (resource category "NERC Reports"). The newest used is the Second Quarter 2026 report (nerc.gov.ng/wp-content/uploads/2026/09/2026_Q2_Report.pdf).
