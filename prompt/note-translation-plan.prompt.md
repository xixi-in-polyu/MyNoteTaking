# Implement Note Translation And Rewrite

Modify the Flask note-taking app in `/Users/xixi/projects/MyNoteTaking`.

## Requirements

- Add server-side AI translation using the existing `COMP_GENAI_API_KEY` stored in `.env`.
- Never expose the API key to browser code.
- Translate both note title and body.
- Support a fixed target-language list including English, Simplified Chinese, Traditional Chinese, Japanese, Korean, Spanish, French, and German.
- Add a Rewrite button that translates and naturally polishes the title and body into the selected language without adding facts.
- Support persisted notes only; disable AI actions for unsaved drafts.
- Show generated output as a preview. Do not overwrite or persist the current note until the user explicitly clicks Apply.
- Add Discard behavior that leaves the current note unchanged.
- Apply generated content through the existing note update endpoint.
- Do not add translation-history database columns.

## Backend

- Extract the GenAI request logic from `Agent.md` into `src/services/translation.py`.
- Use the existing provider endpoint and model configuration.
- Require structured JSON output containing string `title` and `content` fields.
- Handle missing keys, HTTP failures, network failures, invalid JSON, and malformed provider responses.
- Add:
  - `POST /api/notes/<id>/translate`
  - `POST /api/notes/<id>/rewrite`
- Validate the target language and return preview data without committing changes.

## Frontend

Update `src/static/index.html` with:

- Target-language selector.
- Translate and Rewrite buttons.
- Loading and error states.
- Readonly generated title/content preview.
- Apply and Discard controls.
- Disabled AI actions for unsaved notes.
- Existing auto-save must not persist preview output before Apply.

## Validation

- Compile changed Python files.
- Parse the inline JavaScript.
- Use mocked provider calls to verify success, invalid language handling, and preview non-persistence.
- Run diagnostics and `git diff --check`.
- Manually smoke-test the app locally, including Chinese and Japanese selections, preview, Apply, Discard, and mobile layout.
