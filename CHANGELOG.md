# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project loosely follows Semantic Versioning.

---

## [1.5.0] - 2026-04-29

### Added

* Interview Prep tab integrated into the full app with a dedicated top-level workflow for aptitude and interview practice
* New `app/interview_aptitude_prep/` package with isolated modules for:
  * registry-driven set discovery (`registry_ia.json`)
  * question-set loading and validation
  * scoring and answer review
  * optional timed attempts
* Two sample JSON-based practice sets covering quantitative aptitude and data interview fundamentals
* `docs/interview_prep_json_format.md` documenting the registry format, supported question types, scoring fields, timer fields, and authoring conventions for future question sets

### Changed

* About tab and README updated to include the new Interview Prep workflow in feature lists, usage notes, structure references, and limitations
* Interview Prep design leaves room for future API-based coaching or AI-assisted post-attempt review through question-set metadata, without coupling the first version to any backend service

---

## [1.4.0] - 2026-04-26

### Added

* AI Assistant tab integrated into the main full app (`app_resume.py`) with chat-style interaction, quick prompts, long-prompt composer, PDF export, and context-aware grounding against SalaryScope outputs
* Hybrid assistant backend:
  * local runs -> local Ollama
  * Streamlit Cloud runs -> Hugging Face Space
* Hugging Face Space deployment scaffold (`hf_space_app/`) and setup guide (`docs/hf_space_setup.md`) for free-tier cloud assistant hosting
* Per-user AI chat persistence:
  * logged-in users -> Hugging Face dataset-backed history when configured
  * local fallback -> SQLite

### Changed

* Cloud AI assistant usage is now login-gated: anonymous chat is disabled on Streamlit Cloud, while local anonymous testing remains allowed
* AI assistant wording and guardrails updated so responses stay aligned with displayed SalaryScope predictions while still allowing app help, drafting, negotiation tips, job-title clarification, and cautious recommendations
* Cloud assistant path tuned for free Hugging Face Spaces with smaller deployed models, shorter default outputs, continuation handling for truncated drafts, and larger configurable response caps

---

## [1.3.0] - 2026-04-25

### Added

* HR Tools tab (`app/tabs/hr_tools_tab.py`) — dedicated employer-facing section with five compensation planning tools accessible via inner sub-tabs:
  * **Hiring Budget Estimator** (`app/hr_tools/hiring_budget.py`) — estimates total annual payroll cost for an open role given headcount and adjustable employer cost assumptions (benefits %, overhead %, one-time recruiting cost); model estimate shown with full cost breakdown bar chart and CSV export
  * **Salary Benchmarking Table** (`app/hr_tools/benchmarking_table.py`) — generates a reference grid of model predictions across all experience levels for a selected role and location; grid is editable in-place via `st.data_editor` with HR Override, Band Min, Band Max, and Internal Notes columns; visualised as a grouped bar chart with band markers; CSV export
  * **Candidate Comparison** (`app/hr_tools/candidate_comparison.py`) — side-by-side salary estimate comparison for 2 to 5 candidates; each candidate has independent profile inputs and an optional individual override; salary spread across candidates is flagged; CSV export
  * **Offer Competitiveness Checker** (`app/hr_tools/offer_checker.py`) — compares a planned offer against the model's salary estimate for a given profile using a Plotly gauge chart; tiered interpretive guidance (>20% below, 10–20% below, within 10%, above); CSV export
  * **Team Compensation Audit** (`app/hr_tools/team_audit.py`) — CSV upload of current team salaries; vectorised batch prediction run once on upload with result cached in session state; global percentage adjustment for systematic model offset; configurable underpaid/overpaid thresholds; scatter plot of current vs reference, delta histogram, flagged records table, full audit table in expander; CSV export; sample template download

* `app/hr_tools/` package — all HR tool business logic isolated here, independent of `app/tabs/`:
  * `predict_helpers.py` — single-row inference wrappers for App 1 (`predict_app1`) and App 2 (`predict_app2`), each calling `model.predict()` exactly once per invocation; `render_override_widget()` shared UI component; `batch_predict_app1()` and `batch_predict_app2()` vectorised batch helpers for team audit
  * `__init__.py` — package marker

* HR override system present in all five tools:
  * Every single-row tool exposes a collapsible override expander allowing HR to substitute the model estimate with an internal reference value
  * Override reason captured as free text and included in all CSV exports alongside the original model estimate
  * Override state is read from `st.session_state` before `model.predict()` is called, so each tool runs exactly one predict call per render regardless of override state

### Changed

* Tab list in `app_resume.py` extended with `:material/corporate_fare: HR Tools` inserted before About; rendering block follows the same pattern as all other tabs; three-line change only
* README updated to v1.3.0: HR Tools section added to Key Features, Features table, Project Structure, and Future Scope
* `about_tab.py` updated: HR & Employer Tools section added to Features & Modules expander; Tab Guide entry added for HR Tools; Usage Instructions entry added for HR Tools; hero version pill updated to v1.3.0; Shared System Features tab list updated

### Performance

* All single-row tools (Hiring Budget, Offer Checker, Candidate Comparison) read override widget state from `st.session_state` before running inference, eliminating the previous double-predict pattern where `model.predict()` was called once for the widget default and again for the final result
* Benchmarking Table predictions cached via `@st.cache_data` keyed on all input parameters; grid recomputes only when inputs change, not on every widget interaction
* Team Audit batch predictions cached in `st.session_state` keyed on file name and row count; threshold and adjustment controls recompute only Pandas operations, not model inference
* Team Audit batch loop replaced with vectorised `batch_predict_app1` / `batch_predict_app2` helpers that build the full feature DataFrame once and call `model.predict()` once for the entire file
* Plotly imported lazily inside each render function rather than at module load time; `config={"displayModeBar": False}` applied to all charts to reduce JS overhead

---

## [1.2.0] - 2026-04-18

### Added

* `app/model_hub/extended_modes/` package — four schema-driven prediction modes available per loaded Model Hub bundle:
  * `hub_manual_tab.py` — single-row prediction form rendered from schema; result displayed using the same styled `hub_result_card_html` card as the main Model Hub panel
  * `hub_batch_tab.py` — CSV/XLSX upload (up to 10,000 rows), row-by-row prediction with progress bar, summary metrics, results preview table, CSV/XLSX downloads, schema-declared charts, and auto-generated prediction distribution histogram
  * `hub_resume_tab.py` — PDF upload, NLP-based extraction pre-filling an editable review form, extraction quality panel (auto-extracted count, needs-review count, per-field provenance), resume score panel, and prediction; uploading a new PDF clears previous results automatically; explicit Clear button also provided
  * `hub_scenario_tab.py` — up to 5 named scenarios using plain widgets (no `st.form` wrapper, no save step required); `Run All Scenarios` always reads current widget values; comparison table, horizontal bar chart, schema-declared charts, optional sensitivity sweep, CSV export; `Clear Results` button resets between runs
  * `schema_plots.py` — chart renderer driven by the optional `plots` key in `schema.json`; supported types: `gauge`, `bar`, `horizontal_bar`, `scatter`, `histogram`, `line`; single-value chart types rendered in Manual and Resume modes; DataFrame-backed types rendered in Batch and Scenario modes
  * `model_card.py` — Model Card UI component rendered as a collapsible expander per selected model before the Load Model button; sections: identity (name, format badge, version badge, tags, target), performance metrics, use cases (intended/out-of-scope), data and framework, caveats and ethical notes, provenance, external links; degrades gracefully when fields are absent

* `hub_resume_engine.py` — data-driven resume feature extraction engine:
  * All lexicon data (skills, job titles, education patterns, country aliases) loaded from JSON files; no hardcoded lists in Python
  * spaCy `PhraseMatcher` used for skills (same technique as main `resume_analysis.py`); NER used for country extraction; regex used for experience years and education level
  * Every extractor is a pure function returning `ExtractionResult` (value, found flag, source string, extractor\_id); `extractor_id` is stamped on each result so resume scoring works without depending on schema field names
  * `extract_all_fields()` accepts `bundle_lexicons` parameter; lexicons are threaded through the call stack (no global mutation); safe for concurrent Streamlit sessions with different loaded models
  * Regex fallback for skill extraction when spaCy is unavailable
  * Resume score computed from `extractor_id` matching (not field names) so any schema field naming convention works

* `app/model_hub/extended_modes/lexicons/` — four shared global JSON lexicons:
  * `skills.json` — 450+ skill phrases across 20 categories: programming languages, databases, web frontend, web backend, data science core, ML libraries, data engineering, MLOps/deployment, cloud platforms, BI/analytics, DevOps tools, mechanical/civil engineering, electrical/electronics engineering, aerospace/defence, chemical/process engineering, energy/environment, pharmaceutical/drug development, biotechnology/life sciences, neuroscience/medical, mathematics/statistics, cybersecurity
  * `job_titles.json` — 50+ canonical titles with alias lists covering software, data, ML/AI, hardware, mechanical, civil, electrical, aerospace, chemical, energy, environmental, pharmaceutical, biotech, neuroscience, and more; all 50 roles in the STEM salary dataset are covered
  * `education.json` — four education levels (0–3) each with a list of regex patterns; checked highest-to-lowest; patterns are extensible without code changes
  * `countries.json` — two sections: `display_names` (alias → country name, for schemas using "USA", "India") and `iso_codes` (alias → ISO-2 code, for schemas using "US", "IN"); 80+ entries each; longest-match-first

* Per-bundle lexicon override system:
  * Admin upload panel now accepts optional `skills.json` and `job_titles.json` uploads alongside the model bundle
  * `_upload_lexicon_sidecar()` helper uploads each file to the bundle folder on HuggingFace after the main upload; failure is non-fatal and shown as a warning
  * `loader.py` downloads `skills.json` and `job_titles.json` from the bundle folder at load time (with `force=True` so pushed updates take effect immediately) and stores them in `ModelBundle.lexicons`
  * `hub_resume_engine.py` resolves skills and job titles via `_resolve_skills_flat(bundle_lexicons)` and `_resolve_job_titles(bundle_lexicons)`, checking bundle data first and falling back to global JSON files; no process-level cache mutation
  * Registry entry records `has_skills_lexicon` and `has_titles_lexicon` flags

* Model Card upload support:
  * Upload panel expander "Model Card Metadata" with structured input fields: intended use, out-of-scope, limitations, ethical notes, training data, framework, authors, license, tags
  * Raw JSON override textarea for metrics, links, and any other model card fields
  * Assembled dict is merged into the registry entry under `"model_card"` after `upload_bundle()` returns but before `push_registry()`; `uploader.py` is not modified

* `_render_extended_modes_panel()` in `model_hub_tab.py` — renders the four-mode sub-tab bar after the Load Model button; each mode is gated on its import availability flag so removing any file drops that tab silently
* `_render_model_card()` injected into `_render_prediction_panel()` between the model info caption and the divider; appears for every selected model without requiring a bundle to be loaded

* `ModelBundle.lexicons` attribute added to `loader.py`; populated from per-bundle JSON sidecars; defaults to empty dict when no bundle-level lexicons are present

* `schema.json` optional keys `plots` and `scenario_sweep` — fully documented in `docs/model_hub_extended_schema.md`; backward-compatible; schemas without these keys behave identically to before

* `docs/model_hub_extended_schema.md` — complete reference for all extended schema keys, per-bundle lexicon format, extractor identifiers, removal instructions per mode, and session state key conventions

* Three synthetic STEM resume PDFs for testing Model Hub resume extraction: Dr Sarah Chen (Bioinformatics Scientist, US), James Okafor MEng CEng FRAeS (Aerospace Engineer, GB), Priya Rajan (Senior Data Scientist, SG)

* 5,000-row synthetic batch test file (`stem_batch_5k.csv`) crafted from safe high-signal combinations (SE/EX experience, PRIV/STARTUP sector, LG company, T1/T2 city) across all 50 job titles in the STEM salary dataset

### Changed

* `model_hub_tab.py` — duplicate prediction form removed from `_render_prediction_panel`; the Manual tab in the extended modes panel covers single prediction; the panel now stops at the Load Model button and delegates to `_render_extended_modes_panel`
* `hub_batch_tab.py` — `itertuples()` replaced with `df.to_dict("records")` throughout; `itertuples()` silently mangles column names containing spaces, hyphens, or leading digits — `to_dict("records")` preserves exact column names; progress bar instantiation moved from `_run_batch` into the render function (correct Streamlit execution context); file identity tracking and auto-clear on new upload added; explicit Clear button added; layout changed to horizontal row: file uploader / Run / Clear
* `hub_resume_tab.py` — completely rewritten to use `hub_resume_engine.py`; old inline keyword heuristics replaced by the data-driven extraction engine; `_render_prefilled_form` now accepts full schema dict so `layout`, `result_label`, and `plots` keys are preserved when rendering the review form; result card updated from `st.metric` to `hub_result_card_html` matching main Model Hub panel
* `hub_manual_tab.py` — result card updated from `st.metric` to `hub_result_card_html`; `_render_result_card` replaced by `_format_prediction` + `hub_result_card_html` import matching the pattern used in the original `_render_prediction_result`
* `hub_scenario_tab.py` — completely rewritten: `st.form` wrapper removed from each scenario expander; plain widgets are used so `Run All Scenarios` always reads live current values without requiring a save step; `_clear_scenario_inputs()` cleans up widget state keys when a scenario is removed; `_blank_scenario()` replaces `_default_scenario()`; `Clear Results` button added
* `hub_resume_engine.py` — `_compute_score()` rewritten to use `extractor_id` from `ExtractionResult` instead of field name substring matching; `ExtractionResult` gains `extractor_id: str` field; `extract_all_fields()` stamps each result with its extractor identifier; `_render_prefilled_form` schema patching fixed to preserve all top-level schema keys
* `loader.py` — `ModelBundle.__slots__` and `__init__` extended with `lexicons: Optional[dict]`; `load_bundle()` downloads optional `skills.json` and `job_titles.json` from the bundle folder after the existing aliases download; failed parses are logged as warnings and do not abort loading
* README updated to v1.2.0: tagline, key features, Model Hub section (bundle tables, what users/admins see, schema system, access control), resume feature section, scenario feature section, project structure (full `extended_modes/` tree), docs structure, usage instructions, security notes, technologies, future scope, limitations
* `about_tab.py` updated: Model Hub section rewritten to describe all four prediction modes and per-bundle lexicons; Resume Analysis section updated to reflect data-driven engine, 20+ domain coverage, and quality panel; Financial Planning Tools section added; Scenario Analysis updated with no-save-step note; Tab Guide, Usage Instructions, and Limitations updated throughout

### Fixed

* `hub_batch_tab.py` — `itertuples()` silently renaming non-identifier column names (spaces, hyphens, leading digits) causing wrong or missing prediction inputs; fixed by switching to `df.to_dict("records")`
* `hub_resume_engine.py` — `_compute_score()` using hardcoded field names `"education_level"` and `"education"` to find education value; broke for any schema with different field naming; fixed by using `extractor_id`
* `hub_resume_tab.py` — `_render_prefilled_form` discarding `layout`, `result_label`, and `plots` keys from schema; caused review form to always render single-column; fixed by preserving all schema keys and replacing only `"fields"`
* `hub_resume_tab.py` — uploading a second PDF showing stale extraction results from the first PDF beneath the new uploader; fixed by file identity tracking (`name:size`) with automatic state clear on change
* `hub_resume_tab.py` — no way to clear extraction results between resumes; fixed with explicit Clear button
* `hub_scenario_tab.py` — `Run All Scenarios` always using schema default values regardless of widget contents because `st.form` held values in a buffer until its own submit button was clicked; fixed by removing `st.form` wrappers
* `model_hub_tab.py` — Model Hub tab showing the prediction form twice: once in the existing inline panel and again in the Manual sub-tab; fixed by removing the inline form from `_render_prediction_panel`
* `hub_manual_tab.py`, `hub_resume_tab.py` — result displayed as plain `st.metric` instead of the styled `hub_result_card_html` card used by the main Model Hub panel; fixed by importing and using `hub_result_card_html` from `app.theme`

---

## [1.1.0] - 2026-04-15

### Added

* Model Hub tab — allows admins to upload independently trained sklearn-compatible models and serve them to logged-in users through a dynamically generated prediction interface
* `app/model_hub/` package with the following modules:
  * `_hf_client.py` — HuggingFace SDK wrapper for upload, download, and file listing against a private dataset repo
  * `registry.py` — reads and writes `models_registry.json`; handles model activation, deactivation, and rollback by family
  * `loader.py` — downloads model bundles from HuggingFace, enforces file size limits before deserialization, and caches loaded bundles in session state
  * `predictor.py` — builds the feature vector from schema inputs (direct mapping and one-hot expansion for selectbox fields) and calls `model.predict()`
  * `schema_parser.py` — converts `schema.json` field definitions into Streamlit widgets; single dispatch table for all supported UI types
  * `uploader.py` — validates and uploads bundles to HuggingFace; generates versioned folder names; builds registry entries
  * `validator.py` — validates schema structure, per-field constraints, and schema–columns consistency with OHE awareness
* `app/tabs/model_hub_tab.py` — Streamlit UI for the Model Hub; prediction panel, admin upload panel, registry manager, and schema editor
* Bundle versioning: each upload creates a new folder (`model_<timestamp>_<id>/`); existing bundles are never overwritten
* Rollback system: models sharing a `family_id` can be rolled back to any earlier version from the Registry Manager
* Visual schema editor: admins can build `schema.json` field-by-field in the UI and download the result, without editing JSON directly
* Schema upload and validation panel: upload an existing `schema.json` to validate it, preview the generated form, or push it to an existing bundle
* Model size limits enforced at upload: 200 MB for model files, 10 MB for columns files, 512 KB for `schema.json` and `aliases.json`
* Registry stores both `num_inputs` (schema fields shown to the user) and `num_features` (raw model columns) separately; both displayed in the UI
* Session-state caching for loaded bundles to avoid re-downloading on every Streamlit rerun
* `HF_TOKEN` and `HF_REPO_ID` read from `st.secrets` — compatible with Streamlit Cloud and local development
* Security log entry on every `model.pkl` deserialization for audit visibility
* ONNX bundle support: `model.onnx` + `columns.json` format loaded via `onnxruntime` with no arbitrary code execution on deserialization; `columns.json` is plain JSON with no pickle risk; ONNX is the recommended format for new uploads
* `aliases.json` sidecar support: optional display labels for selectbox model values; merged into schema at load time; can be uploaded with the bundle or pushed separately to an existing bundle via the schema editor panel
* Optional `layout` key in `schema.json` enables multi-column form rendering (1, 2, or 3 columns) using per-field `row` and `col_span` keys; fully backward-compatible
* Optional `result_label` key in `schema.json` overrides the prediction result card label shown to users; falls back to the registry `target` field when absent

### Changed

* `_hf_client.py` upload mechanism replaced raw HTTP calls to the deprecated `/upload/` endpoint (which returned HTTP 410) with `huggingface_hub` SDK (`CommitOperationAdd` + `create_commit`)
* `validate_schema_vs_columns` is now OHE-aware: a `selectbox` field whose values expand to `<name>_<value>` columns in `columns.pkl` is no longer flagged as missing
* Model selector area updated to show two separate metrics — **Input Fields** (user-facing) and **Model Features** (raw column count) — with tooltips explaining the difference
* Registry Manager expander updated to show the same two-metric breakdown per model entry
* `huggingface_hub` logger level set to `WARNING` to suppress the informational Xet Storage fallback message during `BytesIO` uploads
* README updated: added Model Hub section, updated project structure, configuration, usage, technologies, security notes, limitations, future scope, and version badge to 1.1.0
* `about_tab.py` updated: added Model Hub subsection, updated tab guide, usage instructions, technologies list, and limitations

### Fixed

* `ImportError` on startup caused by `registry.py` importing `HF_HEADERS`, `HF_API_BASE`, and `REQUEST_TIMEOUT` from `_hf_client.py` after those names were removed in the SDK migration
* False schema–columns mismatch warnings shown during upload when selectbox fields are one-hot encoded in `columns.pkl`
* `st.metric("Features", ...)` showing the raw column count instead of the user-facing input field count in the model selector

---

## [1.0.0] - 2026-04-02

### Added

* Apriori association rule mining for pattern insights (Model 1)
* Admin panel for system monitoring, diagnostics, and feedback analytics
* Currency conversion feature with API integration and fallback system
* Post-tax salary estimation module
* Cost-of-living (COL) adjustment feature
* UI enhancements including captions, usage descriptions, and Material icons

### Changed

* Improved batch prediction usability with clearer instructions and validation messages
* Enhanced overall UI consistency and user experience

### Fixed

* Minor UI inconsistencies and validation issues across modules

---

## [0.4.0] - 2026-03-24

### Added

* Clustering model (KMeans) for career stage segmentation (Model 1)
* User authentication system using SQLite (initial implementation)

### Changed

* Migrated authentication system from SQLite to Firebase Authentication and Firestore

---

## [0.3.0] - 2026-03-09

### Added

* Resume Analysis using SpaCy, Regex and phrase-matching
* Batch prediction functionality for large datasets
* About sections for user guidance
* Model Analytics tab (performance metrics and evaluation plots)
* Data Insights tab (EDA visualizations)
* Classification model for salary level prediction (Model 1)

### Changed

* Merged separate Streamlit applications into a unified system

### Fixed

* Input validation issues in prediction workflows

---

## [0.2.0] - 2026-02-28

### Added

* Streamlit application for general salary prediction (Model 1)
* Streamlit application for data science salary prediction (Model 2)
* Basic multi-tab UI structure for both applications
* Initial prediction workflows and result display
* Power BI dashboards for both datasets

### Changed

* Improved data preprocessing and feature engineering pipelines

---

## [0.1.0] - 2026-02-10

### Added

* Dataset selection (general salary and data science salaries)
* Exploratory data analysis using Jupyter notebooks
* Initial regression model prototypes

---

## [0.0.1] - 2026-01-02

### Added

* Project initialization and scope definition
* Requirement analysis and system planning

---

*Changelog format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)*
