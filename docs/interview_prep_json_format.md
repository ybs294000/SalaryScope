# Interview Prep JSON Format

The Interview Prep feature loads practice sets from JSON files through a small registry file. This keeps the tab extensible without changing application code every time a new set is added.

## Files

The feature uses two layers:

1. `app/interview_aptitude_prep/registry_ia.json`
2. One JSON file per practice set under `app/interview_aptitude_prep/sample_sets/` or another folder inside `app/interview_aptitude_prep/`

## Registry Format

Each entry in `registry_ia.json` tells the UI what to show in the set picker.

```json
{
  "version": 1,
  "title": "Interview Prep Registry",
  "sets": [
    {
      "set_id": "quant_foundations_ds",
      "title": "Quantitative Aptitude Foundations",
      "subtitle": "Core arithmetic and data interpretation practice",
      "description": "Build speed and confidence across percentages, ratios, averages, and practical data reasoning.",
      "file": "sample_sets/quantitative_aptitude_foundations.json",
      "category": "Aptitude",
      "role_family": "Data and Analytics",
      "difficulty": "Intermediate",
      "estimated_minutes": 18,
      "question_count": 6,
      "enabled": true,
      "sort_order": 10,
      "tags": ["quantitative", "percentages"],
      "ai_integration": {
        "enabled": false,
        "provider_hint": "future_api",
        "mode": "post_attempt_review"
      }
    }
  ]
}
```

### Required Registry Fields

- `set_id`
- `title`
- `file`

### Recommended Registry Fields

- `subtitle`
- `description`
- `category`
- `role_family`
- `difficulty`
- `estimated_minutes`
- `question_count`
- `enabled`
- `sort_order`
- `tags`

### Notes

- `file` must point to a JSON file inside `app/interview_aptitude_prep/`
- `set_id` must be unique
- disabled sets are ignored by the UI

## Question Set Format

Each question set is a single JSON object with metadata, timer settings, scoring rules, review settings, and sections.

```json
{
  "set_id": "quant_foundations_ds",
  "title": "Quantitative Aptitude Foundations",
  "description": "A short set for data and analytics candidates.",
  "category": "Aptitude",
  "role_family": "Data and Analytics",
  "difficulty": "Intermediate",
  "estimated_minutes": 18,
  "instructions": [
    "Read each question carefully.",
    "Submit once you are done."
  ],
  "timer": {
    "enabled": true,
    "time_limit_seconds": 1080,
    "enforce_on_submit": true
  },
  "scoring": {
    "default_marks": 1,
    "negative_marks": 0.25,
    "pass_percent": 60
  },
  "review": {
    "show_correct_answers": true,
    "show_explanations": true
  },
  "ai_integration": {
    "enabled": false,
    "provider_hint": "future_api",
    "mode": "post_attempt_review"
  },
  "sections": [
    {
      "id": "percentages_and_ratios",
      "title": "Percentages and Ratios",
      "description": "Core arithmetic questions.",
      "questions": []
    }
  ]
}
```

## Supported Question Types

The current version supports:

- `single_choice`
- `multiple_choice`
- `numeric_input`
- `text_input`
- `dropdown`
- `true_false`

## Question Format

### Single Choice

```json
{
  "id": "qa_01",
  "type": "single_choice",
  "topic": "Percentages",
  "prompt": "What is 15% of 200?",
  "options": [
    { "id": "a", "label": "20" },
    { "id": "b", "label": "25" },
    { "id": "c", "label": "30" },
    { "id": "d", "label": "35" }
  ],
  "correct_answer": "c",
  "marks": 1,
  "negative_marks": 0.25,
  "explanation": "15% of 200 is 30."
}
```

### Multiple Choice

```json
{
  "id": "qa_02",
  "type": "multiple_choice",
  "prompt": "Which statements are correct?",
  "options": [
    { "id": "a", "label": "Statement A" },
    { "id": "b", "label": "Statement B" },
    { "id": "c", "label": "Statement C" }
  ],
  "correct_answer": ["a", "c"],
  "marks": 2,
  "negative_marks": 0.5,
  "explanation": "A and C are both correct."
}
```

### Numeric Input

```json
{
  "id": "qa_03",
  "type": "numeric_input",
  "prompt": "What is 24 divided by 6?",
  "accepted_answers": [4],
  "tolerance": 0,
  "marks": 1,
  "negative_marks": 0.25,
  "placeholder": "Type a numeric answer",
  "explanation": "24 / 6 = 4."
}
```

### Text Input

```json
{
  "id": "qa_04",
  "type": "text_input",
  "prompt": "Name the metric that measures completed purchases divided by exposed users.",
  "accepted_answers": ["conversion rate", "conversion"],
  "case_sensitive": false,
  "marks": 1,
  "negative_marks": 0.25,
  "placeholder": "Type your answer",
  "explanation": "The metric is conversion rate."
}
```

### Dropdown

```json
{
  "id": "qa_05",
  "type": "dropdown",
  "prompt": "Choose the best answer.",
  "options": [
    { "id": "a", "label": "Option A" },
    { "id": "b", "label": "Option B" }
  ],
  "correct_answer": "b",
  "marks": 1,
  "negative_marks": 0.25,
  "explanation": "Option B is correct."
}
```

### True or False

```json
{
  "id": "qa_06",
  "type": "true_false",
  "prompt": "Precision and recall always move together.",
  "correct_answer": "false",
  "marks": 1,
  "negative_marks": 0.25,
  "explanation": "Precision and recall can move in opposite directions."
}
```

## Scoring Rules

- `marks` is the score awarded for a correct answer
- `negative_marks` is deducted for a wrong answer
- skipped questions do not receive a penalty
- `pass_percent` is used for the summary outcome

If a question omits `marks` or `negative_marks`, the set-level defaults are used.

## Timer Rules

- `enabled`: whether the set can run in timed mode
- `time_limit_seconds`: full duration in seconds
- `enforce_on_submit`: whether the app should mark late submissions as time-exceeded during scoring

The current timer model records start and submit timestamps and evaluates the result at submission time. This keeps the timer reliable and easier to maintain.

## AI Integration Placeholder

The `ai_integration` block is optional and is reserved for future API-based review flows, such as:

- answer coaching
- post-attempt feedback
- explanation expansion
- interview follow-up questions

Current UI behavior does not depend on this block, so it is safe to keep it disabled until an AI workflow is added later.

## Validation Tips

When authoring a new set:

- keep `set_id` unique across the registry
- keep every question `id` unique within the set
- make sure each option `id` is stable
- use `accepted_answers` for `numeric_input` and `text_input`
- keep explanations concise and useful
- match `question_count` in the registry to the real number of questions

## Sample Files

Reference examples are included here:

- `app/interview_aptitude_prep/sample_sets/quantitative_aptitude_foundations.json`
- `app/interview_aptitude_prep/sample_sets/data_interview_fundamentals.json`
