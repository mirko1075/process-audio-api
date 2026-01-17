# Testing Policy (pytest)

## Framework Decision
Use **pytest** as the test framework.

Recommended add-ons (only if not already present):
- `pytest-flask` for Flask client fixtures
- `pytest-cov` for coverage

## Mandatory Testing Rule
Any functional change MUST include tests:
- New behavior → new tests
- Bug fix → regression test
- Refactor → existing tests must still pass

## Test Categories
Prefer organizing tests under:
- `tests/unit/` — pure logic
- `tests/api/` — Flask route tests
- `tests/websocket/` — Socket.IO tests
- `tests/security/` — auth and policy tests

## Minimum Coverage Expectations
- Every REST endpoint: at least 1 success + 1 error test.
- Auth flows: at least 1 valid + 1 invalid token test.
- WebSocket: at least 1 connection/auth and 1 message flow test.

## Execution
Baseline commands:
- Discover tests:
  - `pytest --collect-only -q`
- Run tests:
  - `pytest -q`
- Coverage:
  - `pytest --cov --cov-report=term-missing`

## Handling Flaky/Integration Tests
- Integration tests requiring external services must be:
  - clearly marked (e.g., `@pytest.mark.integration`)
  - guarded by env vars
  - skipped by default in CI unless configured
