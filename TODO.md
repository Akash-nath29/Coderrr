# Task: Fix Insufficient Validation of AI-Generated Fixes in Self-Healing

## Issue Description
In src/agent.js, the selfHeal method requests AI-generated fixes for failed steps, but the validation of the returned fixed_step object is incomplete. While it checks for the presence of command for run_command actions, it does not validate required fields for file operations (e.g., path, content, oldContent, newContent), allowing invalid fixes to proceed and cause subsequent failures.

## Solution Implemented

### Changes Made:
- [x] Added `validateFixedStep()` method in `src/agent.js` that validates required fields based on action type:
  - `run_command`: requires `command` (string, non-empty)
  - `create_file`/`update_file`: requires `path` (string, non-empty) and `content` (string)
  - `patch_file`: requires `path`, `oldContent`, and `newContent` (all strings, non-empty)
  - `delete_file`/`read_file`/`create_dir`/`delete_dir`/`list_dir`: requires `path` (string, non-empty)
  - `rename_dir`: requires either `path`+`newPath` or `oldPath`+`newPath` (all strings, non-empty)

- [x] Updated both retry logic blocks in `executePlan()` method to use `this.validateFixedStep(fixedStep)` instead of the incomplete validation that only checked for `command` field

### Validation Logic:
The new validation ensures that:
1. The fixed step is a valid object
2. It has an `action` field
3. Based on the action type, all required fields are present and are non-empty strings where applicable

### Testing:
- The validation will now prevent retries with incomplete AI-generated fixes
- Invalid fixes will be rejected, and the agent will either skip retrying or ask the user for intervention
- This prevents cascading failures from malformed AI responses

## Status: COMPLETED ✅
