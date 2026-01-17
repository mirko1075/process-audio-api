# Change Workflow (AI + Human)

## Default Mode
Read-only unless explicitly authorized.

## Standard Workflow
1. Confirm intent and scope.
2. Map impacted areas:
   - Code
   - Docs (`docs/`)
   - OpenAPI
   - Postman
   - Tests
3. Implement minimal change.
4. Update docs/spec/postman/tests.
5. Run validation commands.
6. Summarize:
   - What changed
   - What was validated
   - Remaining risks / TODOs

## Completion Criteria
A change is complete only if:
- Tests pass (or explicit approved exception)
- Docs updated
- OpenAPI updated and validated
- Postman updated

## Commit Discipline (recommended)
- One logical change per commit
- Commit message includes: scope + reason
- If a change touches API behavior, mention OpenAPI/Postman updates in commit body
