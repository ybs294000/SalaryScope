# SalaryScope AI Assistant Stack

This folder contains the SalaryScope **AI assistant stack** for optional
assistant features such as:

- resume summary generation
- negotiation email / call script generation
- constrained app chatbot support
- persistent chat history
- PDF export of replies and conversations

It is intentionally modular so the assistant can be enabled in selected app
entrypoints without tightly coupling it to the core prediction logic.

## Model choice

The default model is `llama3.2:1b` through **Ollama**.

Why this model:

- reasonably small for local use
- more realistic for CPU-only or limited-RAM demo machines
- strong enough for summarization and prompt-following tasks
- simple local HTTP API
- free to run on your own machine after download

This choice is based on Ollama's official library page, which specifically
positions Llama 3.2 small models for summarization, prompt rewriting, and tool
use: <https://ollama.com/library/llama3.2>

## What this prototype does

- calls a local Ollama server over `http://127.0.0.1:11434`
- stores AI conversation history locally in SQLite
- provides chat modes for app help, prediction explanation, negotiation, resume assistance, and report writing
- exports replies and full conversations to PDF
- keeps all LLM work optional and outside the salary prediction path

## What it does not do

- replace the existing ML salary models
- make percentile / market-truth claims
- provide guaranteed HR or legal advice

## Local setup

1. Install Ollama from: <https://ollama.com/>
2. Pull the default model:

```powershell
ollama pull llama3.2:1b
```

3. Run the model locally:

```powershell
ollama run llama3.2:1b
```

4. In another terminal, start the standalone demo:

```powershell
streamlit run app/local_llm/demo_app.py
```

5. To run the LLM-enabled SalaryScope variant:

```powershell
streamlit run app_resume_llm.py
```

## Optional environment variables

You can override the defaults without editing code:

- `SALARYSCOPE_LLM_BASE_URL`
- `SALARYSCOPE_LLM_MODEL`
- `SALARYSCOPE_LLM_TIMEOUT`

Example:

```powershell
$env:SALARYSCOPE_LLM_MODEL="llama3.2:1b"
streamlit run app/local_llm/demo_app.py
```

## Notes for academic use

- present the LLM as a **drafting assistant**, not as the prediction engine
- keep disclaimers visible
- review generated text before using it in demos or exports
- the chatbot should explain and support displayed outputs, not challenge them
