# Data Enrichment Log

## New Impact Links (14 total, connecting all 10 events to indicators)
See `data/processed/ethiopia_fi_unified_data_enriched.csv`, records LINK_0004–LINK_0014
(3 impact_links existed in source data already: LINK_0001–LINK_0003).
Each row documents parent_id, related_indicator, relationship_type, impact_direction,
impact_magnitude, lag_months, evidence_basis, and confidence.

## New Observations
| record_id | indicator_code | value | location | date | source | confidence |
|---|---|---|---|---|---|---|
| OBS_NEW_01 | ACC_OWNERSHIP | 55% | urban | 2021 | Global Findex 2021 | high |
| OBS_NEW_02 | ACC_OWNERSHIP | 40% | rural | 2021 | Global Findex 2021 | high |

## Schema Note
The source `reference_codes.csv` states impact_link records "link via parent_id",
but no `parent_id` column existed in the raw `ethiopia_fi_unified_data.csv`. We added
this column ourselves when constructing the 14 impact_link records.

## Rationale
Urban/rural disaggregation supports Task 2's required urban vs rural comparison.
Impact links translate the 10 cataloged events into modeled effects on Access/Usage
indicators, required for Task 3's event-indicator matrix.