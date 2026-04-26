# Hugging Face Space Setup For SalaryScope

This guide adds a free Hugging Face Space backend for the AI assistant while
keeping local Ollama as the local-runtime path.

## Architecture

- Local run: SalaryScope -> Ollama
- Streamlit Cloud run: SalaryScope -> Hugging Face Space
- Logged-in user chat history: Hugging Face dataset repo when configured
- Fallback chat history: SQLite for non-logged-in or non-HF-configured cases

## Existing Hugging Face setup in this repo

Your project already has partial Hugging Face setup for the Model Hub:

- `HF_TOKEN`
- `HF_REPO_ID`

These are used by the existing Model Hub code.

## New items you should create

1. A new Hugging Face **Space**
   Suggested name:
   - `salaryscope-assistant`

2. A new Hugging Face **dataset repo** for chat history
   Suggested name:
   - `salaryscope-ai-chat`

## Step 1: Create the Space

On Hugging Face:

1. Create a new Space
2. Choose `Gradio`
3. Visibility:
   - public is easiest for testing
   - private is also possible if you use a token
4. Upload:
   - `hf_space_app/app.py`
   - `hf_space_app/requirements.txt`

## Step 2: Configure the Space model

In the Space settings, add a variable:

- `SPACE_MODEL_NAME = qwen2.5:0.5b`

Optional if you want more room for longer drafts:

- `SPACE_MAX_NEW_TOKENS = 360`

Recommended first choice:

- `qwen2.5:0.5b`

Why:

- ungated
- strong instruction-following
- much better chance of fitting comfortably on a free CPU Space
- still good for drafting/explaining tasks
- can handle longer replies a bit more comfortably when `SPACE_MAX_NEW_TOKENS` is raised

Even lighter fallback:

- `smollm2:360m`

Gemma note:

- `google/gemma-2-2b-it` may require accepting Google's license on Hugging Face first

Llama note:

- Meta Llama models may require license acceptance too

## Step 3: Create the chat history dataset repo

Create a dataset repo such as:

- `your-username/salaryscope-ai-chat`

Private is recommended.

The app stores per-user JSON snapshots there, for example:

- `ai_chat/your_email_or_username.json`

## Step 4: Add Streamlit secrets for the assistant

Add these to `.streamlit/secrets.toml` locally and also to Streamlit Cloud secrets:

```toml
HF_SPACE_URL      = "https://your-space-name.hf.space"
HF_SPACE_API_NAME = "/predict"

HF_CHAT_REPO_ID   = "your-username/salaryscope-ai-chat"
HF_CHAT_TOKEN     = "hf_xxxxxxxxxxxxxxxxxxxx"
```

You can reuse your existing `HF_TOKEN` if it has the required access.

If you prefer to keep one token:

```toml
HF_TOKEN          = "hf_xxxxxxxxxxxxxxxxxxxx"
HF_REPO_ID        = "your-username/salaryscope-models"
HF_CHAT_REPO_ID   = "your-username/salaryscope-ai-chat"
HF_SPACE_URL      = "https://your-space-name.hf.space"
HF_SPACE_API_NAME = "/predict"
```

## Step 5: Streamlit Cloud behavior

The assistant now routes automatically:

- if local runtime -> local Ollama
- if Streamlit Cloud runtime -> Hugging Face Space

This is based on the same local/cloud detection style used elsewhere in the app.

## Step 6: Test checklist

1. Verify the Space opens in browser
2. In the Space footer, click `Use via API`
3. Confirm endpoint name is `/predict`
4. Run the LLM app locally:

```powershell
python -m streamlit run app_resume_llm.py
```

5. For cloud testing, deploy the LLM app version or wire the same secrets into Streamlit Cloud

## Notes

- Free CPU Spaces sleep when idle
- First response may be slow
- Free CPU inference for 2B-3B models can still be slow
- Hugging Face dataset repos are not real databases, so this setup is suitable for academic/demo scale, not heavy production traffic

## Suggested first cloud model

Use:

- `Qwen/Qwen2.5-0.5B-Instruct`

Only move to Qwen 1.5B, Qwen 3B, Gemma, or Llama after the basic cloud path works.
