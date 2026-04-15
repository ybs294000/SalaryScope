# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project loosely follows Semantic Versioning.

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
* Model size limits enforced at upload: 200 MB for `model.pkl`, 10 MB for `columns.pkl`, 512 KB for `schema.json`
* Registry stores both `num_inputs` (schema fields shown to the user) and `num_features` (raw model columns) separately; both displayed in the UI
* Session-state caching for loaded bundles to avoid re-downloading on every Streamlit rerun
* `HF_TOKEN` and `HF_REPO_ID` read from `st.secrets` — compatible with Streamlit Cloud and local development
* Security log entry on every `model.pkl` deserialization for audit visibility

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
* `st.metric("Features", ...)` showing the raw column count (8) instead of the user-facing input field count (4) in the model selector

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