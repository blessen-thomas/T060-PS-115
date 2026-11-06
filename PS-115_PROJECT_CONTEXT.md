# PS-115 Capstone --- Project Context and Operating Rules

**Purpose:** This is the source-of-truth context file for Antigravity
IDE. Read it at the beginning of every session and before every new
feature. Follow the official problem statement and supplied data pack.
Never invent missing rules.

## 1. Project identity

-   Team ID: **T060**
-   Problem: **PS-115 --- Municipal Building-Plan Approval Fee and FAR
    Compliance Engine**
-   Members: Bheemesh V (1AT24CG016), Blessen Thomas (1AT24CG017)
-   Repository: https://github.com/blessen-thomas/T060-PS-115
-   Local path: `D:\project\T060-PS-115`
-   Python 3.10+, CLI/file-driven backend. No frontend is required.
-   The team must understand the implementation and be able to explain
    and modify it during the viva.

## 2. Mandatory agent instructions

1.  Read this entire file at the start of every new session, after a
    restart, and before beginning a new task.
2.  Inspect the actual repository before editing: `git status`, recent
    commits, source files, tests, and data files. Do not recreate
    completed work.
3.  The original PS-115 brief, supplied sample-data README, CSV files,
    and `commands.txt` are authoritative. If this file conflicts with
    them, flag the conflict and follow the authoritative source.
4.  Never invent a formula, threshold, default, rounding rule, date
    interpretation, fee basis, or missing value. Search the supplied
    sources first. If still unspecified, stop that specific decision,
    report the ambiguity, and ask for clarification or make it
    explicitly configurable only with approval.
5.  Keep code simple, readable, beginner-friendly, and viva-friendly.
    Avoid unnecessary abstractions, dependencies, frameworks, modules,
    files, or documentation.
6.  Batch related work into coherent milestones. Prefer more meaningful
    implementation per prompt, but do not combine unrelated subsystems
    into an unreviewable change.
7.  Add tests for new behavior and boundary cases. Preserve existing
    tests.
8.  Before proposing any commit, run `python -m pytest -v`,
    `git diff --check`, inspect the full diff, and check Git status.
9.  **Never commit or push without the user's explicit approval.** Show
    the proposed commit message and wait.
10. Never modify the original supplied data pack. Work from the
    repository copy in `data/`.
11. Process `commands.txt` strictly in original file order. Do not skip
    or reorder commands.
12. Never claim something is complete unless it is implemented and
    verified.
13. After each milestone, report briefly: changes, tests, files changed,
    Git state, unresolved specification questions, and next milestone.
14. Prioritize core business rules and required output files over
    optional polish.

## 3. Official business rules

This is the working transcription of the supplied PS-115 rules. Verify
against the original brief/data pack before implementation.

### 3.1 FAR

-   Residential base FAR:
    -   Road width `<12 m`: **1.75**
    -   Road width `12–18 m`, inclusive: **2.25**
    -   Road width `>18 m`: **2.50**
-   Commercial base FAR = corresponding residential FAR **+0.25**.
-   Mixed-use base FAR = residential base FAR.
-   FAR = eligible built-up area / plot area.
-   Exclude stilt parking, parking basements, and **10% of balcony
    area** from FAR area.
-   Premium FAR: up to **+0.50**, only on roads at least **12 m** wide.
    -   Residential charge rate: **40% of guidance value per sqm**.
    -   Commercial charge rate: **60% of guidance value per sqm**.
-   TDR: up to **+0.40**.
-   Premium FAR + TDR must not exceed **+0.60** above base FAR.

### 3.2 Ground coverage

-   Plot area `<=200 sqm`: maximum **65%**.
-   Plot area `201–500 sqm`: maximum **60%**.
-   Plot area `>500 sqm`: maximum **50%**.
-   Ground-floor footprint includes stilt.

### 3.3 Setbacks and corner plots

-   Front setback by road width:
    -   `<12 m`: **3 m**
    -   `12–18 m`, inclusive: **4.5 m**
    -   `>18 m`: **6 m**
-   Side/rear setback by plot width:
    -   `<=9 m`: **1 m**
    -   `>9 m` through `12 m`: **1.5 m**
    -   `>12 m`: **2 m**
-   Corner plot: larger road is the front road; add **0.5 m** to the
    side setback along the second road.
-   Equal-width corner roads are a boundary case. Follow the supplied
    convention; do not invent a tie-breaker.

### 3.4 Height

-   Geometric height limit = **1.5 × (effective road width + required
    front setback)**.
-   Permitted height is the lower of the geometric limit and the
    applicable zone cap.
-   Residential cap: **15 m** for road width `<12 m`; otherwise **24
    m**.
-   Commercial cap: **30 m**.
-   Mixed-use height follows residential.
-   Corner plots use the larger road width.
-   Each floor above the base height allowance requires **0.5 m
    additional setback on all sides**.
-   **Unresolved:** the rule summary does not establish a universal
    base-floor allowance. Do not assume four floors or hardcode a
    default. Verify the official source or obtain an explicit decision.
-   Height deviations at completion are never compoundable.

### 3.5 Parking

-   Residential: 1 car per unit with carpet area `>100 sqm`; 1 car per 2
    units with carpet area `<=100 sqm`.
-   Commercial: 1 car per **50 sqm**.
-   Shortfall `<=20%`: permitted with **₹2,00,000 per missing car**.
-   Shortfall `>20%`: violation.
-   **Unresolved:** do not automatically round fractional parking
    requirements up unless the official source says to. Preserve exact
    fractional results by default. Do not invent how mixed-use
    residential and commercial parking requirements combine.

### 3.6 Fees

-   Scrutiny: **₹20/sqm built-up area**, minimum **₹2,000**.
-   Development charge: residential **₹300/sqm**; commercial
    **₹600/sqm**.
-   Betterment levy: **2% of plot guidance value** if converted from
    agricultural use.
-   Labour cess: **1% of estimated construction cost**, using
    **₹1,800/sq ft**.
-   All fees rounded **up to the nearest ₹10**.
-   Permitted parking shortfall fee: ₹2,00,000 per missing car.
-   **Unresolved:** do not invent premium FAR chargeable-area basis or a
    mixed-use premium rate. Verify source material and flag if absent.

### 3.7 Workflow

-   `SUBMITTED` → `SCRUTINY` (**7 days**) → `SITE_INSPECTION` (**10
    days**) → `TECHNICAL` (**15 days**) → `APPROVED` or `QUERY`.
-   A query stops the workflow clock.
-   Applicant must respond within **30 days** or the application lapses.
-   A lapsed application can be revived once within **60 days**, on
    payment of **25% of scrutiny fee**.
-   Deemed approval: elapsed working time, excluding query pauses,
    **exceeds 45 working days**, provided no violations were listed at
    scrutiny.
-   Working days: Monday--Friday excluding supplied holidays.
-   Workflow timers start only after fees are paid.
-   For the supplied expected behavior, counting starts on the next
    working day after fee payment.
-   Do not confuse the 30-day query response period with working-day
    workflow clocks; use the exact unit specified by the rule.

### 3.8 Approval validity and commencement

-   Approval valid for **2 years**.
-   One extension of **1 year** at **10% of original fees**.
-   A second extension must be rejected.
-   Commencement must be reported within **6 months**, otherwise
    approval is suspended.
-   Revalidation after suspension costs **₹5,000**.

### 3.9 Completion certificate and deviations

-   Deviation percentage =
    `(as-built built-up - approved built-up) / approved built-up × 100`.
-   Built-up deviation `<=5%`: compound at **2× development charge** on
    excess area.
-   Deviation `>5% and <=10%`: compound at **4× development charge**.
-   Deviation `>10%`: non-compoundable; refuse CC.
-   Setback deviation `<=0.3 m`: **₹10,000 per metre-side**.
-   Height deviation is never compounded; refuse CC.
-   Output decision values: `CC_ISSUED` or `CC_REFUSED`.
-   Reported deviation percentage: 2 decimal places.

### 3.10 Precedence and gating

Apply checks in this order: 1. Zoning permitted use 2. FAR (base,
premium, TDR cap) 3. Ground coverage 4. Setbacks and corner rules 5.
Height and extra-height setback 6. Parking

Fees are calculated only if there are no non-compoundable violations.
Workflow timers begin only after fees are paid.

## 4. Required boundary and planted cases

At minimum, test: - Road exactly **12 m**. - Plot exactly **200 sqm**. -
Corner plot with equal road widths. - Premium FAR `0.50` + TDR `0.40`
exceeds combined cap by `0.30`. - Parking shortfall exactly **20%**. -
Query response on day **30**. - Working-day count crossing a Monday
holiday. - Built-up deviation exactly **5%** and exactly **10%**.

Additional planted cases from the supplied README (use these to test
general rules; never hardcode application IDs into business logic):

  -----------------------------------------------------------------------
  Application                         Expected rule behavior
  ----------------------------------- -----------------------------------
  APP-0002                            12 m road: base FAR 2.25, front
                                      setback 4.5 m, residential zone cap
                                      24 m; premium 0.25 allowed

  APP-0005                            200 sqm plot: 65% coverage; 126 sqm
                                      footprint = 63%, compliant

  APP-0024                            Equal 9 m corner roads: 3 m front,
                                      2.5 m second-road side

  APP-0003                            Premium 0.50 + TDR 0.40 exceeds
                                      combined 0.60 cap by 0.30

  APP-0017                            8 units above 100 sqm + 4 units up
                                      to 100 sqm; 10 cars required; 8
                                      proposed; exactly 20% shortfall,
                                      allowed; fee for 2 cars

  APP-0019                            Query response on 30th calendar day
                                      is in time; query pauses workflow
                                      clock

  APP-0001                            Fees paid Jan 9; skips Jan 15 and
                                      Jan 26 holidays; deemed approval
                                      Mar 18 (46th working day), if no
                                      scrutiny violations

  APP-0009                            Approved 273 sqm; as-built 286.65
                                      sqm = +5%; 2× development charge on
                                      excess

  APP-0007                            Approved 408 sqm; as-built 448.80
                                      sqm = +10%; 4× slab, not refused

  APP-0032                            Commercial use in residential-only
                                      zone `ZN-R1`

  APP-0035                            FAR above base on a 10 m road

  APP-0026                            Premium FAR requested on a 9 m road

  APP-0014                            Coverage above 60% for 201--500 sqm
                                      plot

  APP-0015                            Front setback 4 m on 15 m road; 4.5
                                      m required

  APP-0018                            Side setback 1.2 m on 10.5 m plot
                                      width; 1.5 m required

  APP-0029                            Rear setback 1.5 m on 15 m plot
                                      width; 2 m required

  APP-0020                            Corner second-road side setback 2.2
                                      m; 2.5 m required

  APP-0031                            16 m building on 7.5 m road exceeds
                                      15 m zone cap

  APP-0027                            12 cars required, 9 proposed; 25%
                                      shortfall

  APP-0021                            Commercial, premium 0.50 + TDR
                                      0.10, but built FAR exceeds base +
                                      0.60

  APP-0006                            As-built +12%; CC refused

  APP-0010                            Setback deviation 0.30 m on 2
                                      sides; ₹6,000

  APP-0013                            As-built height +0.40 m; CC refused

  APP-0023                            No response within 30 days →
                                      LAPSED; revive within 60 days with
                                      25% scrutiny fee, then respond and
                                      continue

  APP-0008                            Approved Feb 25; no commencement
                                      within 6 months → suspended Aug 25;
                                      ₹5,000 revalidation, then
                                      commencement

  APP-0011                            First extension at 10% original
                                      fees; second extension rejected

  APP-0034                            Clean application but fees never
                                      paid; clock never starts; no deemed
                                      approval
  -----------------------------------------------------------------------

## 5. Data pack and required outputs

Expected input data includes zoning tables, holiday list, 40
applications, floors data, `commands.txt` with **292 commands**, and the
supplied README.

-   Original pack:
    `D:\documents\T060-PS-115-sample-data\T060-PS-115-sample-data\`
-   Working copy: repository `data/` directory.
-   Do not edit the original pack.
-   Execute `commands.txt` in exact source order.

Required output files and exact columns:

**`validation_report.csv`**
`app_id,rule_id,check,required,proposed,compoundable` - One row per
violation per application. - Emit a `NONE` row if no violations. - Sort
by app ID, then rule precedence.

**`fee_demand.csv`**
`app_id,built_up_sqm,far_area_sqm,far_achieved,far_allowed,scrutiny_fee,development_charge,premium_far_fee,betterment_levy,labour_cess,parking_shortfall_fee,total_fee`

**`workflow.csv`**
`app_id,stage,entered_date,exited_date,working_days,clock_stopped_days,status_after,deemed_approval_date`

**`cc_decisions.csv`**
`app_id,request_date,deviation_pct,area_compounding_fee,setback_compounding_fee,height_deviation_m,decision`

Other output conventions: - Working days: Monday--Friday excluding
supplied holidays. - Workflow starts next working day after fee
payment. - `deviation_pct`: 2 decimal places. - Decision: `CC_ISSUED` or
`CC_REFUSED`. - Fees: round up to nearest ₹10. - Hidden evaluation may
compare output fields directly; preserve exact column names and order.

## 6. Current progress --- verify before relying on it

Previously reported completed/pushed milestones: - Project structure,
initial docs, dependencies. - FAR tests and input validation. - CLI. -
FAR rounding fix to prevent false approvals. - Base FAR by use and road
width. - Eligible-area exclusions, premium FAR, TDR cap. - CSV data
loader and interval lookup. - Zoning validation. - Ground coverage
validation. - Setback and corner-plot validation.

Latest reported state: - Height and parking code was present in
`src/rules.py` and tests in `tests/test_rules.py`. - Latest reported
test result: **108 passed**. - `git diff --check` passed. - Latest
reported uncommitted diff: `src/rules.py` and `tests/test_rules.py`. -
Functions reported: `check_building_height(...)`,
`calculate_extra_height_setback(...)`,
`calculate_required_parking(...)`, `check_parking(...)`. - Base-floor
limit was changed to a required parameter (no invented default). -
Parking preserves fractional requirements by default; optional
`round_up=True`. - APP-0017 exact 20% and APP-0027 25% parking cases
were tested. - Proposed commit:
`feat(validation): add height and parking validation checks`. - Do
**not** assume this commit was made. Check Git status and log first.

Previously reported commit hashes (verify with `git log`; this is not a
complete history): -
`5d83bcd chore: initialize project structure, docs, and dependencies` -
`6b6710d test(far): add comprehensive pytest suite for FAR logic and input validation` -
`3d85bb0 feat(cli): add interactive command-line interface for FAR checks` -
`c79253f fix(far): prevent false approvals caused by rounding` -
`2aa10a7 feat(far): derive base FAR from building use and road width` -
`0d9ccff feat(far): implement eligible area exclusions, premium FAR, and TDR caps` -
`f2976ae feat(data): add CSV data loader and interval lookup module` -
`9632d4f feat(validation): add ground coverage validation` - Zoning and
setback/corner commits were also reported; retrieve exact
hashes/messages from Git, do not guess.

## 7. Remaining milestones

1.  **Finish height and parking:** verify extra-floor setback is
    enforced against proposed setbacks; resolve base-floor allowance;
    confirm fractional parking and mixed-use interpretation from source;
    test; review; ask before commit.
2.  **Fee engine:** implement all fee components and exact output
    schema. Verify premium chargeable-area basis and mixed-use rates
    from authoritative sources. Apply ceiling-to-nearest-₹10. Do not
    produce fees if non-compoundable violations exist.
3.  **Workflow engine:** stages, fee-paid gate, working-day/holiday
    logic, query pause, response deadline, lapse, one-time revival,
    deemed approval. Verify APP-0001, APP-0019, APP-0023, APP-0034.
4.  **CC engine:** built-up deviation slabs, setback compounding, height
    deviations, expiry, one-time extension, commencement deadline,
    revalidation. Verify APP-0006, APP-0007, APP-0009, APP-0010,
    APP-0011, APP-0013, APP-0008.
5.  **End-to-end integration:** process all 40 applications and 292
    commands in order; generate all four CSVs; test deterministic
    output; do not hardcode planted IDs.
6.  **Submission artifacts:** README/run instructions; design PDF
    (glossary, class diagram, state diagram, business-rule register);
    10--20 one-line decision log; 5-minute demo (main flow + two edge
    cases); viva readiness for both members.

## 8. Git policy

-   Continue on existing `main` unless user says otherwise.
-   Make meaningful commits after coherent milestones.
-   Before asking to commit: run full tests, `git diff --check`, inspect
    diff and status, then show proposed commit message.
-   Never commit or push without explicit approval.
-   Do not rewrite published history.
-   Do not claim GitHub is updated until push succeeds and status/log
    confirm it.

## 9. User communication preferences

-   User wants more useful implementation per prompt and fewer prompts.
-   Avoid unnecessary tasks, repeated audits, extra files, and long
    explanations.
-   When asked, provide concise, paste-ready Antigravity prompts.
-   Explain important logic simply so the user can defend it in the
    viva.
-   Ask only when a genuine specification ambiguity blocks correct
    implementation.
-   Do not ask the user to repeat context already recorded here.

## 10. Mandatory startup checklist

At the beginning of a new Antigravity session: 1. Read this entire file.
2. Run `git status --short --branch`. 3. Run `git log -5 --oneline`. 4.
Inspect project tree, source, tests, and `data/`. 5. Run
`python -m pytest -v`. 6. Report verified state, especially whether
height/parking is committed. 7. Continue from the next incomplete
milestone. Do not restart or duplicate completed work.
