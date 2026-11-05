# PS-115 – Municipal Building-Plan Approval Fee and FAR Compliance Engine — Sample Data Pack

Prepared by 10 SECONDS for Team T060.

## Files

| File | What it holds | Row count |
|---|---|---|
| `zones.csv` | 4 zones with category, permitted uses and height caps | 4 data rows |
| `far_table.csv` | Base FAR by zone and road-width band (band edges explicit) | 12 data rows |
| `setback_table.csv` | Front setback by road width; side/rear setback by plot width | 6 data rows |
| `coverage_table.csv` | Maximum ground coverage by plot-area band | 3 data rows |
| `holidays.csv` | 2026 holiday list for the working-day clock | 12 data rows |
| `fee_schedule.csv` | Fee rates from the brief | 14 data rows |
| `applications.csv` | 40 building-plan applications (clean ones and one per violation type) | 40 data rows |
| `floors.csv` | Built-up area by floor for every application (basement, stilt, upper floors) | 178 data rows |
| `commands.txt` | Submissions, ~120 payment/stage/query/commencement/extension/CC events and print requests | 292 command lines (excluding comments) |

Row numbers quoted below are 1-based data-row numbers (the header is row 0). Line numbers for `commands.txt` are physical line numbers including comment lines.

## Column reference

Conventions: dates `YYYY-MM-DD`; timestamps `YYYY-MM-DD HH:MM:SS` (24h, IST, no timezone suffix); money in Rs as plain decimals with 2 places (no commas, no symbol); percentages as plain numbers (12.5 means 12.5%); booleans `true`/`false`; IDs uppercase with a fixed prefix. An empty cell means "not applicable" and is only allowed where the notes say so.

### `zones.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| zone_id | string | ZN-xx | — | — |
| zone_name | string | — | — | — |
| zone_category | enum | — | RESIDENTIAL, COMMERCIAL, MIXED | MIXED takes residential FAR/height values |
| permitted_uses | string | semicolon list | RESIDENTIAL, COMMERCIAL, MIXED | — |
| height_cap_road_lt_12_m | decimal | m | — | — |
| height_cap_road_ge_12_m | decimal | m | — | — |

### `far_table.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| zone_id | string | — | zones.csv | — |
| road_width_from_m | decimal | m | — | — |
| from_inclusive | bool | — | — | — |
| road_width_to_m | decimal | m | — | 99 = no upper limit |
| to_inclusive | bool | — | — | — |
| base_far | decimal | — | — | — |

### `setback_table.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| setback_type | enum | — | FRONT, SIDE_REAR | — |
| measure | enum | — | ROAD_WIDTH, PLOT_WIDTH | what the band is measured on |
| from_m | decimal | m | — | — |
| from_inclusive | bool | — | — | — |
| to_m | decimal | m | — | — |
| to_inclusive | bool | — | — | — |
| setback_m | decimal | m | — | — |

### `coverage_table.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| plot_area_from_sqm | decimal | sq m | — | — |
| from_inclusive | bool | — | — | — |
| plot_area_to_sqm | decimal | sq m | — | — |
| to_inclusive | bool | — | — | — |
| max_coverage_pct | decimal | % | — | ground footprint incl. stilt / plot area |

### `holidays.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| holiday_date | date | — | — | not a working day |
| holiday_name | string | — | — | — |

### `fee_schedule.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| fee_code | string | — | — | — |
| rate | decimal | — | — | see unit |
| unit | string | — | — | — |
| notes | string | — | — | may be empty |

### `applications.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| app_id | string | APP-nnnn | — | — |
| applicant_name | string | — | — | — |
| survey_no | string | — | — | — |
| zone_id | string | — | zones.csv | — |
| proposed_use | enum | — | RESIDENTIAL, COMMERCIAL, MIXED | — |
| plot_width_m | decimal | m | — | frontage; drives side/rear setback |
| plot_depth_m | decimal | m | — | — |
| plot_area_sqm | decimal | sq m | — | width x depth |
| road_width_m | decimal | m | — | main road |
| is_corner_plot | bool | — | — | — |
| second_road_width_m | decimal | m | — | corner plots only, else empty |
| front_setback_m | decimal | m | — | proposed |
| side_setback_1_m | decimal | m | — | proposed |
| side_setback_2_m | decimal | m | — | proposed; on corner plots this is the second-road side |
| rear_setback_m | decimal | m | — | proposed |
| ground_footprint_sqm | decimal | sq m | — | incl. stilt, for coverage |
| building_height_m | decimal | m | — | proposed |
| premium_far_requested | decimal | FAR | — | 0 = none |
| tdr_far_requested | decimal | FAR | — | 0 = none |
| units_carpet_above_100 | int | units | — | residential units with carpet > 100 sq m |
| units_carpet_upto_100 | int | units | — | residential units with carpet <= 100 sq m |
| parking_proposed | int | cars | — | commercial need = commercial built-up / 50 (floors.csv) |
| agri_converted | bool | — | — | true = betterment levy |
| guidance_value_per_sqm | decimal | Rs per sq m | — | plot guidance value |
| submitted_date | date | — | — | — |

### `floors.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| app_id | string | — | applications.csv | — |
| floor_no | string | — | B1, G, 1, 2, ... | G is stilt when floor_use is PARKING |
| floor_use | enum | — | PARKING, RESIDENTIAL, COMMERCIAL | PARKING floors (stilt/basement) are excluded from FAR |
| built_up_sqm | decimal | sq m | — | includes balcony |
| balcony_sqm | decimal | sq m | — | balcony part of built_up_sqm (FAR exclusion rule applies) |

## Command file format

`commands.txt` holds one command per line in the form `COMMAND_NAME|arg1|arg2|...`. Commands must be processed strictly in file order. Lines starting with `#` are comments and blank lines are ignored. An argument written as `-` means "not applicable". Every command used in this pack:

| Command | Arguments (in order) | Meaning |
|---|---|---|
| `SUBMIT` | `app_id|submit_date` | Validate and issue the fee demand (if no non-compoundable violations) |
| `PRINT_VALIDATION` | `app_id` | — |
| `FEE_PAYMENT` | `app_id|pay_date|amount|challan_ref` | Fees paid; the workflow clock starts on the next working day |
| `STAGE_RESULT` | `app_id|stage|result_date|result` | stage SCRUTINY, SITE_INSPECTION, TECHNICAL; result CLEARED, QUERY or APPROVED (TECHNICAL only) |
| `QUERY_RESPONSE` | `app_id|response_date` | Applicant reply to a QUERY |
| `REVIVE` | `app_id|request_date` | Revive a lapsed application (25% of scrutiny fee, paid by the FEE_PAYMENT that follows) |
| `COMMENCEMENT` | `app_id|report_date` | — |
| `REVALIDATION_FEE` | `app_id|pay_date|amount` | — |
| `EXTENSION` | `app_id|request_date` | One-time 1-year extension at 10% of the original fees |
| `CC_REQUEST` | `app_id|request_date|as_built_built_up_sqm|setback_deviation_m|sides_deviating|as_built_height_m` | Completion certificate request; as-built built-up is total over all floors (same basis as floors.csv) |
| `PRINT_CC` | `app_id` | — |
| `PRINT_FEE_DEMAND` | `app_id` | — |
| `PRINT_WORKFLOW` | `app_id|as_of_date` | — |

## Planted scenarios

Every edge case in the brief, mapped to the exact record where it occurs, followed by extra traps.

- **EC-01 Road width exactly 12 m**
  - APP-0002: road width exactly 12.00 m — falls in the 12–18 m band (base FAR 2.25, front setback 4.5 m, height cap 24 m) and premium FAR (0.25) is allowed (roads >= 12 m) — `applications.csv row 2`
- **EC-02 Plot of exactly 200 sq m**
  - APP-0005: plot 8.00 x 25.00 = exactly 200.00 sq m — the <= 200 band applies (65% coverage); ground footprint 126.00 sq m = 63.00% — compliant, but it would breach the 60% band of a 201+ sq m plot — `applications.csv row 5`
- **EC-03 Corner plot with two roads of equal width**
  - APP-0024: corner plot on two 9.00 m roads — either road may be the front (3.0 m); the second road side needs side setback + 0.5 m (2.50 m); side_setback_2_m is the second-road side — `applications.csv row 24`
- **EC-04 Premium 0.5 plus TDR 0.4 exceeding the combined cap by 0.3**
  - APP-0003: premium FAR 0.50 + TDR 0.40 = 0.90 over base on a 15 m road — exceeds the base + 0.6 combined cap by 0.30 -> violation (FAR cap), no fees computed — `applications.csv row 3`
- **EC-05 Parking shortfall at exactly 20%**
  - APP-0017: 8 units above 100 sq m + 4 units up to 100 sq m -> 8 + 2 = 10 cars required, 8 proposed = exactly 20% shortfall — allowed, shortfall fee 2 x Rs 200000.00 — `applications.csv row 17`
- **EC-06 Query response on the 30th day**
  - APP-0019: TECHNICAL raises a QUERY; the applicant responds on the 30th calendar day — in time, clock resumes (query days excluded from the 45 working days) — `commands.txt lines 126, 155`
- **EC-07 Working-day count crossing a holiday that falls on a Monday**
  - APP-0001: fees paid 2026-01-09 (Fri); SCRUTINY and SITE_INSPECTION cleared, TECHNICAL never decides. The working-day clock skips Mon 2026-01-26 (Republic Day) and Thu 2026-01-15; the 45 working days are exceeded on 2026-03-18 (46th working day) -> DEEMED_APPROVED (no violations at scrutiny) — `commands.txt lines 6, 62`
- **EC-08 Built-up deviation at exactly 5% and at exactly 10%**
  - APP-0009: approved built-up 273.00 sq m, as-built 286.65 = exactly +5% -> compounded at 2x the development charge on the excess; APP-0007: approved 408.00, as-built 448.80 = exactly +10% -> 4x slab (not refused; only ABOVE 10% is refused) — `commands.txt lines 200, 211`
- **Extra traps (not in the brief, but realistic):**
  - One application per violation type, each with exactly that violation (validation report only, no fees): APP-0032 commercial building in residential-only zone ZN-R1 (use not permitted — first in precedence); APP-0035 FAR above base on a 10 m road (no premium); APP-0026 premium FAR requested on a 9 m road (< 12 m) — not permitted; APP-0014 ground coverage above 60% on a 201–500 sq m plot; APP-0015 front setback 4.00 m on a 15 m road (needs 4.5 m); APP-0018 side setback 1.20 m on a 10.5 m wide plot (needs 1.5 m); APP-0029 rear setback 1.50 m on a 15 m wide plot (needs 2.0 m); APP-0020 corner plot: second-road side 2.20 m, needs 2.0 + 0.5 = 2.5 m; APP-0031 16.00 m (stilt + 4 floors) on a 7.5 m road — above the 15 m cap for roads < 12 m; APP-0027 10 + 2 = 12 cars required, 9 proposed = 25% shortfall (> 20%); APP-0021 commercial, premium 0.5 + TDR 0.1 used, built FAR still above base + 0.6 — `applications.csv row 32, applications.csv row 35, applications.csv row 26, applications.csv row 14, applications.csv row 15, applications.csv row 18, applications.csv row 29, applications.csv row 20, applications.csv row 31, applications.csv row 27, applications.csv row 21`
  - APP-0006: as-built +12% built-up — above 10%, not compoundable, CC REFUSED — `commands.txt line 207`
  - APP-0010: setback deviation 0.30 m on 2 sides (on the 0.3 m limit) — compounded at Rs 10000 x 0.3 x 2 = Rs 6000.00 — `commands.txt line 194`
  - APP-0013: as-built height 0.40 m above approved — height deviation is never compounded, CC REFUSED even though area and setbacks are fine — `commands.txt line 192`
  - APP-0023: no response within 30 days -> LAPSED; REVIVE 25 days after lapse (within 60) with 25% of the scrutiny fee, then response and approval — `commands.txt lines 136, 171, 172, 174`
  - APP-0008: approved 2026-02-25, commencement not reported within 6 months -> SUSPENDED on 2026-08-25; revalidation fee Rs 5000.00 paid, then commencement — `commands.txt lines 183, 184`
  - APP-0011: first EXTENSION granted at 10% of the original fees; the second EXTENSION request must be REJECTED (one-time only) — `commands.txt lines 176, 185`
  - APP-0034: clean application whose fees are never paid — workflow clock never starts, so it can never be deemed approved — `applications.csv row 34`

## What is NOT in this pack

Expected outputs are not provided for this set. Validate your engine with your own test suite against the rules in your brief (BR-01 … BR-nn). A separate hidden input set with the same schema will be used at final evaluation; outputs are compared field-for-field, so follow the column formats above exactly in your own output.

## Output format expected at evaluation

Produce these CSV files (header row, same conventions as above, rows sorted as stated). Where the brief is silent on a format detail the choice below is binding for evaluation.

### `validation_report.csv`

One row per violation per application (an application with none gets one row with rule_id `NONE`), ordered by app_id then precedence.

Columns, in order: `app_id`, `rule_id`, `check`, `required`, `proposed`, `compoundable`

### `fee_demand.csv`

One row per application with fees computed.

Columns, in order: `app_id`, `built_up_sqm`, `far_area_sqm`, `far_achieved`, `far_allowed`, `scrutiny_fee`, `development_charge`, `premium_far_fee`, `betterment_levy`, `labour_cess`, `parking_shortfall_fee`, `total_fee`

### `workflow.csv`

One row per stage transition per application, in date order.

Columns, in order: `app_id`, `stage`, `entered_date`, `exited_date`, `working_days`, `clock_stopped_days`, `status_after`, `deemed_approval_date`

### `cc_decisions.csv`

One row per CC_REQUEST.

Columns, in order: `app_id`, `request_date`, `deviation_pct`, `area_compounding_fee`, `setback_compounding_fee`, `height_deviation_m`, `decision`

Binding choices: `working_days` counts Mon–Fri excluding holidays.csv, starting the working day after the fee payment; `deviation_pct` = (as-built − approved built-up) / approved built-up x 100, 2 decimals; `decision` CC_ISSUED or CC_REFUSED; `status_after` one of SCRUTINY, SITE_INSPECTION, TECHNICAL, QUERY, LAPSED, REVIVED, APPROVED, DEEMED_APPROVED, SUSPENDED; fees rounded UP to the next Rs 10.
