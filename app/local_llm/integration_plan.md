# Minimal Integration Plan

This note describes how to connect the standalone local LLM prototype to the
main app later with minimal risk.

## Recommended first hook

Use the prototype only after a salary prediction already exists.

Best first hook:

- Manual prediction result panel

Why:

- it already has structured inputs
- the user has context for the generated script
- failure is non-critical

## Smallest possible UI addition later

Add one expander near the existing salary output:

- title: `AI Draft Assistant (Local)`
- controls:
  - script type
  - tone
  - optional target salary
  - generate button

## Call flow

1. User gets normal ML prediction.
2. User opens the expander.
3. User clicks generate.
4. App calls `generate_negotiation_script(...)`.
5. Output appears in a text area.

## Failure handling

If the local Ollama server is down:

- show a warning
- keep the rest of the page fully usable
- do not retry automatically in a loop

## Guardrails

- never use the LLM for salary estimation
- never describe the LLM draft as market truth
- never block PDF/report generation on LLM success
- keep prompts grounded in existing app fields

## Good follow-up

After negotiation script support is stable, the next optional hook can be:

- Resume Analysis result area -> Resume Summary Draft
