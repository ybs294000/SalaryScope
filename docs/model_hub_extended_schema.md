# Model Hub Extended Modes — Documentation

## Overview

This document covers the **Extended Prediction Modes** feature added to the
Model Hub.  Extended modes allow a Model Hub bundle to be used in four
prediction workflows — Manual, Batch, Resume, and Scenario — without changing
any core application code.

All behaviour is driven by the bundle's `schema.json`.  Two new optional top-level
keys (`plots` and `scenario_sweep`) let schema authors declare charts and
sensitivity sweeps that are rendered automatically in the appropriate mode.

---

## What was added and where

### New files

```
app/model_hub/extended_modes/__init__.py       -- package marker
app/model_hub/extended_modes/schema_plots.py  -- chart renderer (reads schema plots key)
app/model_hub/extended_modes/hub_manual_tab.py   -- Manual Prediction mode
app/model_hub/extended_modes/hub_batch_tab.py    -- Batch Prediction mode
app/model_hub/extended_modes/hub_resume_tab.py   -- Resume Analysis mode
app/model_hub/extended_modes/hub_scenario_tab.py -- Scenario Analysis mode
docs/model_hub_extended_schema.md             -- this file
```

### Modified files

The original extended-modes rollout centered on `app/tabs/model_hub_tab.py`.
Later iterations also updated surrounding Model Hub files so per-bundle
lexicons and `resume_config.json` could participate in Resume mode cleanly.
The minimal integration point in the main UI remains `app/tabs/model_hub_tab.py`:

```
# EXTENDED MODES - BEGIN  (imports block, near the top)
# EXTENDED MODES - END

# EXTENDED MODES - BEGIN  (call site inside _render_prediction_panel)
# EXTENDED MODES - END
```

Subsequent versions expanded the supporting implementation, but the user-facing
contract described in this document remains the same.

---

## How to remove extended modes entirely

1. Delete `app/model_hub/extended_modes/` (the whole directory).
2. Open `app/tabs/model_hub_tab.py` and delete everything between the two
   `EXTENDED MODES - BEGIN` / `EXTENDED MODES - END` comment pairs.
3. Also delete the `_render_extended_modes_panel` function (clearly labeled
   with a docstring mentioning this removal contract).

That is all.  No other file references these modules.

## How to remove a single mode

To remove, for example, the Resume mode only:
1. Delete `app/model_hub/extended_modes/hub_resume_tab.py`.
2. In `model_hub_tab.py`, delete the `try/except` block that imports
   `hub_resume_tab` (guarded by `_HUB_RESUME_AVAILABLE`).
3. The tab disappears from the UI automatically because the availability flag
   drives tab list construction.

---

## User experience

After loading a Model Hub bundle, a divider and a sub-tab bar appear below
the existing "Run a Prediction" panel:

```
[existing single-prediction form and result]

-- Additional Prediction Modes --
[ Manual | Batch | Resume | Scenario ]
```

Each tab is independently usable.  They all share the same loaded bundle and
schema, but maintain independent session state (results, uploads, scenarios)
namespaced by `model_id`.

---

## Extended Schema Reference

### Existing schema keys (unchanged)

The following keys were already supported before this feature and continue to
work identically:

```json
{
  "layout":       { "columns": 2 },
  "result_label": "Predicted Annual Salary (USD)",
  "fields": [
    {
      "name":     "experience_years",
      "type":     "int",
      "ui":       "slider",
      "label":    "Years of Experience",
      "help":     "Total years of professional experience.",
      "min":      0,
      "max":      40,
      "default":  5,
      "row":      1,
      "col_span": 2
    },
    {
      "name":    "job_title",
      "type":    "category",
      "ui":      "selectbox",
      "values":  ["Data Scientist", "ML Engineer", "Data Analyst"],
      "default": "Data Scientist",
      "aliases": {
        "Data Scientist": "Data Scientist (Research focus)",
        "ML Engineer":    "Machine Learning Engineer"
      }
    }
  ]
}
```

All field types and UI widgets documented in the original schema system work
the same as before in all four extended modes.

---

### New top-level key: `plots`

`plots` is an optional list of chart descriptors.  Each descriptor is rendered
in the appropriate mode:

- **Manual and Resume** modes render `gauge`, `bar`, and `horizontal_bar` charts
  (single-value chart types that work with one prediction result).
- **Batch and Scenario** modes render all chart types including `scatter`,
  `histogram`, and `line` (which require a DataFrame of results).

```json
{
  "fields": [ ... ],
  "plots": [
    {
      "type":  "gauge",
      "title": "Predicted Salary Gauge",
      "min_val": 0,
      "max_val": 300000,
      "height": 350
    },
    {
      "type":    "histogram",
      "title":   "Salary Distribution",
      "x_field": "predicted_salary_usd",
      "bins":    40,
      "height":  350
    },
    {
      "type":    "bar",
      "title":   "Average Salary by Experience Level",
      "x_field": "experience_level",
      "y_field": "predicted_salary_usd",
      "height":  350
    },
    {
      "type":    "scatter",
      "title":   "Salary vs Remote Ratio",
      "x_field": "remote_ratio",
      "y_field": "predicted_salary_usd",
      "color_field": "experience_level",
      "height":  400
    }
  ]
}
```

#### Plot descriptor fields

| Field | Required | Default | Description |
|---|---|---|---|
| `type` | yes | -- | Chart type: `gauge`, `bar`, `horizontal_bar`, `scatter`, `histogram`, `line` |
| `title` | no | `""` | Chart title shown above the plot |
| `height` | no | `350` | Chart height in pixels |
| `x_field` | context | -- | Column name for x-axis. For batch/scenario charts: a column in the result DataFrame. For single-value bar charts: a field name from `raw_input` |
| `y_field` | context | -- | Column name for y-axis (batch/scenario charts) |
| `color_field` | no | -- | Column name for color grouping (scatter, line, bar) |
| `size_field` | no | -- | Column name for bubble size (scatter only) |
| `value_field` | no | -- | For gauge: field name in `raw_input` to read value from. If absent, uses the prediction result value |
| `min_val` | no | `0` | For gauge: minimum of the scale |
| `max_val` | no | auto | For gauge: maximum of the scale (defaults to 1.5x the value) |
| `bins` | no | `30` | For histogram: number of histogram bins |
| `bars` | no | -- | For single-value bar: list of `{label, field}` where `field` is a `raw_input` key or `"__result__"` |
| `label` | no | -- | Axis/series label override |

#### Notes on `bars` for single-value bar charts

When a bar chart needs to show multiple fields from a single prediction (not
batch results), use the `bars` key:

```json
{
  "type":  "bar",
  "title": "Compensation Breakdown",
  "label": "USD",
  "bars": [
    { "label": "Predicted Base",   "field": "__result__" },
    { "label": "Years Experience", "field": "experience_years" },
    { "label": "Education Score",  "field": "education_level" }
  ]
}
```

`"__result__"` is a special sentinel that maps to the scalar prediction value.

#### Batch/scenario bar and line charts

When `x_field` and `y_field` are both set and batch results are available,
the chart groups by `x_field` and aggregates `y_field` by mean.  The `x_field`
and `y_field` values must be column names present in either the uploaded file
(batch) or the scenario results DataFrame.

For batch mode, the predicted value column is named after the `result_label`
with spaces replaced by underscores and lowercased.  For example, if
`result_label` is `"Predicted Salary USD"`, the column is
`"predicted_salary_usd"`.

For scenario mode, an additional `"scenario"` column and a `"predicted_value"`
column are always present in the chart DataFrame alongside all input fields.

---

### New top-level key: `scenario_sweep`

`scenario_sweep` is an optional object that configures the sensitivity sweep
in the Scenario Analysis mode.  When present, a sweep chart appears below the
scenario comparison bar chart.

```json
{
  "fields": [ ... ],
  "scenario_sweep": {
    "field":  "experience_years",
    "mode":   "range",
    "min":    0,
    "max":    40,
    "steps":  41
  }
}
```

For a categorical sweep:

```json
{
  "scenario_sweep": {
    "field":        "experience_level",
    "mode":         "values",
    "values":       ["EN", "MI", "SE", "EX"],
    "value_labels": {
      "EN": "Entry Level",
      "MI": "Mid Level",
      "SE": "Senior Level",
      "EX": "Executive Level"
    }
  }
}
```

#### `scenario_sweep` fields

| Field | Required | Default | Description |
|---|---|---|---|
| `field` | yes | -- | Schema field name to sweep. Must match a field in `fields`. |
| `mode` | no | `"range"` | `"range"` for continuous numeric sweep, `"values"` for discrete categorical sweep |
| `min` | range only | `0` | Start of the sweep range |
| `max` | range only | `100` | End of the sweep range |
| `steps` | range only | `50` | Number of evenly-spaced steps between `min` and `max` |
| `values` | values only | `[]` | Explicit list of values to sweep |
| `value_labels` | no | `{}` | Display labels for each value in the sweep (used on the chart x-axis) |

The sweep runs with a user-selected baseline scenario (one of the defined
scenarios).  All inputs are held at the baseline values except the sweep field,
which is varied across the range or values.  This mirrors the sensitivity sweep
in the main Scenario Analysis tab for built-in models.

---

## Batch Prediction mode details

### File requirements

- Supported formats: CSV, XLSX
- Maximum rows: 10,000 per upload
- Column names must exactly match the `name` fields in the schema (case-sensitive)
- Extra columns in the file are ignored
- Column order does not matter

### Predicted value column naming

The predicted value column in the results file is named after the schema's
`result_label` (or the registry `target` field if no `result_label` is set),
with spaces converted to underscores and lowercased.

Example: `result_label = "Predicted Salary USD"` produces column
`predicted_salary_usd`.

### Download formats

Results can be downloaded as CSV or XLSX.  Both formats include the original
input columns plus the predicted value column.

---

## Resume Analysis mode details

### How field extraction works

The resume mode extracts values from PDF text using keyword matching on field
names.  The following field name patterns are recognised:

| Field name contains | What is extracted |
|---|---|
| `experience` or `years` | Years of experience (numeric, from regex patterns) |
| `education` or `edu_level` | Education level as integer 0-3 (High School to PhD) |
| `country` or `location` or `residence` | ISO-2 country code (from a small lookup table) |
| `age` | Age as integer (from regex, validated 18-70) |
| `senior` | Seniority flag 0 or 1 (from title keywords in text) |
| `job_title` or `title` | Job title string (from role/position patterns) |

Fields whose names do not match any of the above keywords are left at their
schema default value and listed in a yellow warning so the user can correct
them manually before running prediction.

All extracted values are pre-filled into editable widgets in the review form.
The user can edit any field before clicking Predict.

### Limitations

- Extraction accuracy depends on resume formatting and the keywords present.
- Only PDF format is supported.
- Resume mode requires `pdfplumber` and `spaCy` to be installed.  If they
  are absent (e.g. lite app), a warning is shown and the tab is hidden
  automatically.

---

## Manual Prediction mode details

The Manual tab inside the extended modes panel is functionally equivalent to
the existing Model Hub "Run a Prediction" panel that already appears above it.
It exists to provide a consistent tab interface alongside Batch, Resume, and
Scenario, and as a clean starting point if the top-level panel is simplified
in future.

It renders the same schema-driven form, calls the same `predict()` function,
and shows the result metric.  Currency conversion is included if available.

---

## Scenario Analysis mode details

### Scenario management

- Up to 5 scenarios can be added.
- Each scenario has an editable name and its own copy of the schema form.
- Scenarios persist in session state until the page is refreshed or the model
  is changed.
- Removing a scenario removes it from the list immediately.

### Comparison output

- A table showing the predicted value for each scenario.
- A horizontal bar chart comparing predicted values across scenarios.
- Schema-declared charts (from `plots`) rendered against a mini DataFrame
  built from scenario results (contains `scenario`, `predicted_value`, and all
  input field columns).
- A sensitivity sweep chart if `scenario_sweep` is defined in the schema.

### Export

Results including all input fields and predicted values can be exported as CSV.

---

## Full schema example with all optional keys

```json
{
  "layout": { "columns": 2 },
  "result_label": "Predicted Salary (USD)",
  "fields": [
    {
      "name":     "experience_years",
      "type":     "int",
      "ui":       "slider",
      "label":    "Years of Experience",
      "help":     "Total years of professional experience in any role.",
      "min":      0,
      "max":      40,
      "default":  5,
      "row":      1,
      "col_span": 2
    },
    {
      "name":    "education_level",
      "type":    "int",
      "ui":      "selectbox",
      "label":   "Education Level",
      "values":  [0, 1, 2, 3],
      "default": 1,
      "aliases": {
        "0": "High School",
        "1": "Bachelor's Degree",
        "2": "Master's Degree",
        "3": "PhD"
      },
      "row": 2,
      "col_span": 1
    },
    {
      "name":    "experience_level",
      "type":    "category",
      "ui":      "selectbox",
      "label":   "Experience Level",
      "values":  ["EN", "MI", "SE", "EX"],
      "default": "MI",
      "aliases": {
        "EN": "Entry Level",
        "MI": "Mid Level",
        "SE": "Senior Level",
        "EX": "Executive Level"
      },
      "row": 2,
      "col_span": 1
    },
    {
      "name":    "company_size",
      "type":    "category",
      "ui":      "selectbox",
      "label":   "Company Size",
      "values":  ["S", "M", "L"],
      "default": "M",
      "aliases": {
        "S": "Small (under 50 employees)",
        "M": "Medium (50-250 employees)",
        "L": "Large (over 250 employees)"
      },
      "row": 3,
      "col_span": 1
    },
    {
      "name":    "remote_ratio",
      "type":    "int",
      "ui":      "slider",
      "label":   "Remote Work (%)",
      "min":     0,
      "max":     100,
      "default": 50,
      "step":    50,
      "row":     3,
      "col_span": 1
    }
  ],
  "plots": [
    {
      "type":    "gauge",
      "title":   "Predicted Salary",
      "min_val": 0,
      "max_val": 300000,
      "height":  300
    },
    {
      "type":    "histogram",
      "title":   "Salary Distribution (Batch)",
      "x_field": "predicted_salary_usd",
      "bins":    40
    },
    {
      "type":    "bar",
      "title":   "Average Salary by Company Size",
      "x_field": "company_size",
      "y_field": "predicted_salary_usd"
    },
    {
      "type":        "scatter",
      "title":       "Salary vs Remote Ratio",
      "x_field":     "remote_ratio",
      "y_field":     "predicted_salary_usd",
      "color_field": "experience_level"
    }
  ],
  "scenario_sweep": {
    "field":        "experience_years",
    "mode":         "range",
    "min":          0,
    "max":          40,
    "steps":        41
  }
}
```

---

## Session state key conventions

All session state keys used by extended modes follow the pattern:

```
mh_ext_{mode}_{purpose}_{model_id}
```

Examples:
- `mh_ext_manual_result_model_20260415_ab12cd`
- `mh_ext_batch_result_model_20260415_ab12cd`
- `mh_ext_resume_text_model_20260415_ab12cd`
- `mh_ext_scenario_scenarios_model_20260415_ab12cd`

The `model_id` namespace ensures that switching between models clears
stale results without needing explicit state resets.

---

## Extensibility

### Adding a new chart type

1. Add a new `elif chart_type == "your_type":` branch in
   `schema_plots.py::_render_single_plot`.
2. Write the corresponding `_render_your_type(...)` function in the same file.
3. Add `"your_type"` to the docstring of `render_schema_plots`.
4. Document the descriptor fields in this file.

No other file needs changing.

### Adding a new extraction heuristic to resume mode

Add an entry to `_KEYWORD_EXTRACTORS` in `hub_resume_tab.py`:

```python
("your_keyword", your_extractor_fn, "type_hint"),
```

where `your_extractor_fn(text: str) -> value | None`.  The keyword is matched
as a substring of the field name (lowercased).  No other file needs changing.

### Adding a new prediction mode

1. Create `app/model_hub/extended_modes/hub_yourmode_tab.py` with a
   `render_hub_yourmode_mode(active_bundle, selected_meta, msg_fn)` function.
2. Add a guarded import and availability flag in `model_hub_tab.py` (inside
   the `EXTENDED MODES - BEGIN/END` block).
3. Add the tab label and call in `_render_extended_modes_panel`.

---

## Compatibility with existing models

The `plots` and `scenario_sweep` keys are fully optional.  Schemas that do
not include them behave identically to before in all modes.  Existing uploaded
bundles require no changes to work in the extended modes panel.

The only change visible to existing Model Hub users is the appearance of the
"Additional Prediction Modes" sub-tab bar below the existing prediction panel
when a bundle is loaded.

---

## Bundle folder structure — what lives where and why

A natural question is whether the extended modes files (lexicons, hub_* modules)
should live inside a model bundle folder on HuggingFace rather than in the app
package. The answer is no, and here is the precise reasoning.

### What a bundle folder contains (HuggingFace, per upload)

```
models/model_20260415_ab12cd/
    model.onnx          (or model.pkl)       -- the trained model artifact
    columns.json        (or columns.pkl)     -- ordered feature column names
    schema.json                              -- user-facing input field definitions
    aliases.json                             -- optional display label sidecar
```

These are **model-specific artifacts** that vary per upload. Every upload gets
its own versioned folder and the files are immutable once written.

### What the app package contains (deployed with the app)

```
app/model_hub/extended_modes/
    hub_resume_engine.py     -- extraction engine (application logic)
    hub_resume_tab.py        -- Streamlit UI (application logic)
    hub_batch_tab.py         -- application logic
    hub_manual_tab.py        -- application logic
    hub_scenario_tab.py      -- application logic
    model_card.py            -- application logic
    schema_plots.py          -- application logic
    lexicons/
        skills.json          -- shared extraction knowledge
        job_titles.json      -- shared extraction knowledge
        education.json       -- shared extraction knowledge
        countries.json       -- shared extraction knowledge
```

These are **application-level assets** that are shared across ALL models.
They contain domain knowledge about how to extract information from resumes,
not knowledge about any specific model.

### Why lexicons belong in the app package

The lexicons (skills, job titles, education patterns, country maps) are used by
`hub_resume_engine.py` to parse free-form PDF text from resumes. This parsing
is entirely independent of which model will receive the extracted values. A model
that predicts software salaries and a model that predicts healthcare salaries both
benefit from the same skill lexicon. Uploading a copy per bundle would:

- Create redundancy -- the same 200 countries would be stored N times on HuggingFace.
- Require every admin uploading a bundle to also supply lexicon files they did not author.
- Make lexicon improvements (adding a new country, skill, or education pattern)
  require re-uploading every existing bundle rather than just redeploying the app.

Updating lexicons is an **app deployment event**, not a bundle upload event.
The correct workflow is: edit the JSON file in source control, redeploy.

### What IS per-model (in the bundle folder)

The `schema.json` is genuinely per-model. It defines which fields the model
expects, their types, UI widgets, allowed values, aliases, layout, plots, and
the scenario sweep configuration. Two models predicting different things need
completely different schemas. This is why schema.json lives in the bundle folder
and is downloaded by `loader.py` on every `load_bundle()` call.

The `model_card` metadata lives in `models_registry.json` (at the HuggingFace
repo root) under the model's registry entry. This is the right place because:
- It is human-readable and editable without re-uploading the model.
- It travels with the registry entry when models are listed, activated, or
  rolled back.
- The admin can update it without disturbing the model artifact.

---

## Bugs fixed in this revision

### hub_batch_tab.py -- itertuples() column name mangling

**Problem:** `df.itertuples()` silently renames columns that are not valid Python
identifiers. A column named `"experience level"` (with a space) becomes
`experience_level` in the NamedTuple, and `getattr(row, "experience level")`
returns `None`. This produced silent wrong predictions for any schema field
whose name contained spaces, hyphens, or leading digits.

**Fix:** Replaced `itertuples()` with `df.to_dict("records")`, which returns
a list of plain dicts and preserves exact column names regardless of content.

### hub_resume_engine.py -- score computation depended on field names

**Problem:** `_compute_score()` looked up experience and education values from
`results` by checking `if "experience" in key.lower()` and
`extracted.get("education_level", extracted.get("education", 1))`. This broke
for any schema that named the field differently (e.g. `"years_exp"`,
`"edu"`, `"level"`).

**Fix:** Added `extractor_id: str` to the `ExtractionResult` dataclass.
Every extractor now stamps the result it returns with its own identifier.
`_compute_score()` now iterates `results.values()` and filters on
`res.extractor_id == "experience"` / `"education"`, which is schema-name
independent.

### hub_resume_tab.py -- _render_prefilled_form lost layout keys

**Problem:** `_render_prefilled_form` built `patched_schema = {"fields": patched_fields}`,
discarding all other top-level schema keys (`layout`, `result_label`, `plots`).
This caused the review form to always render in single-column layout even when
the schema declared `"layout": {"columns": 2}`.

**Fix:** Changed the function to accept the full `schema` dict, then rebuild
`patched_schema` as a copy of the original with only the `"fields"` key
replaced. All other keys are preserved and passed through to `render_schema_form`.

### model_hub_tab.py -- model_card had no upload-time entry point

**Problem:** `model_card.py` reads a `"model_card"` key from the registry entry,
but `uploader.py` never produces this key. Admins had no way to populate it
except manually editing `models_registry.json` on HuggingFace.

**Fix:** Added a collapsible "Model Card Metadata" expander to the upload panel
with structured input fields (intended use, out-of-scope, limitations, ethical
notes, training data, framework, authors, license, tags) plus a raw JSON override
text area for metrics and links. The assembled dict is merged into the registry
entry after `upload_bundle()` returns but before `push_registry()` is called.
`uploader.py` is intentionally not touched -- the model card is a UI-layer
concern, not a bundle artifact concern.

---

## Adding new extractors to hub_resume_engine.py

1. Write a function with the signature:
   `def _extract_yourname(text: str, field: dict, context: dict) -> ExtractionResult`

2. Return `ExtractionResult(value=..., found=True/False, source="...", extractor_id="yourname")`.
   Note: `extract_all_fields()` now stamps `extractor_id` automatically, so the
   extractor itself does not need to set it (but it can if it wants).

3. Add one entry to `_EXTRACTOR_REGISTRY`:
   `"yourname": _extract_yourname`

4. Optionally add one entry to `_FIELD_NAME_TO_EXTRACTOR`:
   `("keyword_in_field_name", "yourname")`
   so fields are matched automatically by name without requiring an explicit
   `"extractor"` key in the schema.

5. Document the new extractor identifier in this file and in
   `docs/model_hub_extended_schema.md`.
