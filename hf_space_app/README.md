# SalaryScope HF Space App

This folder is a standalone Hugging Face Space app for cloud inference.

It is intended to be uploaded as a separate **Gradio Space** and called by the
main SalaryScope Streamlit app when the app is running on Streamlit Cloud.

## What it does

- accepts the payload format used by `app/local_llm/hf_space_client.py`
- runs a local Transformers model inside the Space
- returns a JSON response with generated text
- exposes `/predict` as a Gradio API endpoint

## Recommended starting model

For a free CPU Space, the safest starting option is:

- `qwen2.5:3b` -> `Qwen/Qwen2.5-3B-Instruct`

If you want to try Gemma instead:

- `gemma2:2b` -> `google/gemma-2-2b-it`

Important:

- Gemma and Llama models may require license acceptance on Hugging Face
- free CPU Spaces can still be slow for 2B-3B models
- use one active model per Space, not many

## Space secret / variable

Set this in the Hugging Face Space:

- `SPACE_MODEL_NAME`

Recommended values:

- `qwen2.5:3b`
- `gemma2:2b`
- `llama3.2:1b`
- `llama3.2:3b`

## Files to upload to the Space

- `app.py`
- `requirements.txt`

Optional:

- this README

## Local test

```powershell
pip install -r requirements.txt
python app.py
```

## Expected payload

The Space expects a single JSON object like:

```json
{
  "task": "assistant_chat",
  "model_name": "qwen2.5:3b",
  "messages": [
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "Explain this prediction briefly."}
  ],
  "temperature": 0.2,
  "num_predict": 220
}
```

## Response shape

```json
{
  "content": "Generated response text",
  "model": "qwen2.5:3b",
  "active_repo": "Qwen/Qwen2.5-3B-Instruct",
  "requested_model": "qwen2.5:3b",
  "task": "assistant_chat"
}
```
