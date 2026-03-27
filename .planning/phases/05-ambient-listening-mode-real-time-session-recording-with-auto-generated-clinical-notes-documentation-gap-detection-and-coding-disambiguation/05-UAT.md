---
status: testing
phase: 05-ambient-listening-mode
source: [05-01-SUMMARY.md, 05-02-SUMMARY.md, 05-03-SUMMARY.md]
started: 2026-03-24T21:45:00Z
updated: 2026-03-24T21:45:00Z
---

## Current Test

number: 2
name: Demo Encounter Selection
expected: |
  Page shows a mode selector (Demo Encounter / Live Recording). Selecting "Demo Encounter" shows a dropdown with two encounters listed.
awaiting: user response

## Tests

### 1. Navigation Entry
expected: Ambient Mode appears in sidebar nav under "Ambient" group with mic icon. Clicking it loads the Ambient Listening Mode page with title and description.
result: issue
reported: "start button wasnt enable at start, its mic that was enabled. also after the session we got to know that while transcribing Processing failed: No module named 'faster_whisper'"
severity: major

### 2. Demo Encounter Selection
expected: Page shows a mode selector (Demo Encounter / Live Recording). Selecting "Demo Encounter" shows a dropdown with two options: "Primary Care Follow-Up: CKD Stage 3 with HTN and DM2" and "Urgent Care Visit: Acute Chest Pain with Shortness of Breath".
result: [pending]

### 3. Start Demo Session
expected: Selecting a demo encounter and clicking the start button processes briefly (~1.5s) then transitions to results view with 4 tabs (Transcript, Generated Note, Clinical Findings, Disambiguation).
result: [pending]

### 4. Transcript Display
expected: Transcript tab shows the full doctor-patient conversation (800+ words), session metadata (session ID, duration, demo badge), and word count metric.
result: [pending]

### 5. Generated Note Display
expected: Generated Note tab shows a structured SOAP note with clinical section headers (Chief Complaint, HPI, Assessment, Plan) rendered in readable format.
result: [pending]

### 6. Clinical Findings
expected: Clinical Findings tab shows NER entity count, ICD-10 code count, and completeness score metrics. Below that: entity summary, ICD-10 code cards with descriptions and confidence, and CDI analysis sections (documentation gaps, missed diagnoses, code conflicts in expanders).
result: [pending]

### 7. Disambiguation Review
expected: Disambiguation tab shows 4-5 items, each in a bordered container with colored category badge (gap=amber, missed_diagnosis=blue, conflict=red, ambiguity=orange), title, description, suggested action, and Accept/Dismiss buttons.
result: [pending]

### 8. Accept/Dismiss Interaction
expected: Clicking "Accept" on a disambiguation item updates its display to show accepted status (green badge) and removes the buttons. Clicking "Dismiss" shows dismissed status. Progress counter at bottom updates (e.g., "2 of 5 items reviewed").
result: [pending]

### 9. New Session Reset
expected: Clicking "New Session" button resets the page back to the initial idle state with mode selector and encounter dropdown. Previous results are cleared.
result: [pending]

### 10. Session State Persistence
expected: After loading demo results, navigate to another page (e.g., Pipeline Runner) and back to Ambient Mode. Results are still displayed without needing to reload.
result: [pending]

### 11. Live Recording Path
expected: Selecting "Live Recording" mode shows an audio input widget (st.audio_input microphone recorder). Start button behavior changes to accommodate live recording flow.
result: [pending]

## Summary

total: 11
passed: 0
issues: 1
pending: 10
skipped: 0

## Gaps

- truth: "Start button is enabled and mic widget appears after clicking Start"
  status: failed
  reason: "User reported: start button wasnt enable at start, its mic that was enabled. also Processing failed: No module named 'faster_whisper'"
  severity: major
  test: 1
  root_cause: "Live mode showed st.audio_input before Start button; faster-whisper not pip-installed"
  artifacts:
    - path: "ui/pages/ambient_mode.py"
      issue: "st.audio_input shown in idle state before Start; button disabled until audio recorded"
  missing:
    - "Restructure live mode: Start button first, mic in recording state"
    - "Install faster-whisper dependency"
  debug_session: ""
