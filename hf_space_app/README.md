---
title: SalaryScope Assistant
emoji: 🤖
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: "5.0.0"
python_version: "3.10"
app_file: app.py
pinned: false
---

# SalaryScope Assistant

This Space provides a lightweight API backend for the SalaryScope AI assistant.

It is intended to be called by the main SalaryScope Streamlit app when the app
is running on Streamlit Cloud.

## Recommended model

For a free CPU Space, start with:

- `qwen2.5:1.5b` -> `Qwen/Qwen2.5-1.5B-Instruct`

If that works comfortably and you want stronger output quality, then try:

- `qwen2.5:3b` -> `Qwen/Qwen2.5-3B-Instruct`

## Variable to set in Space settings

- `SPACE_MODEL_NAME`

Suggested values:

- `qwen2.5:1.5b`
- `qwen2.5:3b`
- `gemma2:2b`
- `llama3.2:1b`
- `llama3.2:3b`

## Endpoint

This Space exposes a Gradio API endpoint at:

- `/predict`

The main SalaryScope app sends a JSON payload and expects a JSON response with
generated text.
