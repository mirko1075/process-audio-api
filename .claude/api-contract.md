# API Contract Policy (OpenAPI + Postman)

## Core Principle
**OpenAPI is the contract for REST.** Code must match the contract.

## OpenAPI Rules
- Maintain a single spec file (prefer one of):
  - `openapi.yaml` (preferred)
  - `openapi.json`
- Every REST endpoint must be represented.
- Schemas must match actual request/response payloads.
- Error responses must be documented (at least: 400, 401, 404, 500).
- Auth requirements must be explicit per route.

## Postman Rules
- Maintain a Postman collection JSON (e.g., `postman_collection.json`).
- Postman should be generated from OpenAPI where feasible.
- Define an environment file template (e.g., `postman_environment.example.json`) listing variables.

## Operational Workflow
For any REST change:
1. Update OpenAPI spec first (or in same change).
2. Regenerate/update Postman collection.
3. Run OpenAPI validation.
4. Ensure tests cover at least one happy path and one error path.

## Validation Commands (examples)
- OpenAPI lint/validate (choose one tool and standardize in repo):
  - `python -m pip install openapi-spec-validator && openapi-spec-validator openapi.yaml`
  - or `npm i -g @redocly/cli && redocly lint openapi.yaml`

If the repo already has a preferred validator, use that.
