# Repository conventions

- `msgloom` names the repository and overall distribution. `message_ingest/`
  contains the Scrapy project for acquiring messages from external providers.
- Use the installed, pinned Scrapy version. Keep traversal in spiders, transport
  policy in downloader middleware, persistence in pipelines, and lifecycle work
  in extensions.
- Keep every Python module below 500 lines, including comments and docstrings.
- Document behavior beside the code. Explain inputs, outputs, ownership, failure
  handling, ordering, and resume constraints when they are not obvious. Update
  those comments whenever behavior changes.
- Follow Scrapy's PEP 257 and reStructuredText docstring style. Use a concise
  summary, then a blank line before details. Keep short docstrings on one line;
  put the quotes of multiline blocks on separate lines. Use double backticks
  for literals and Sphinx roles such as `:class:`, `:meth:`, and `:exc:` for API
  references. Wrap prose and ordinary `#` comments at 79 columns. Keep URLs and
  Scrapy contract directives intact. See the source references in
  `docs/component-layout.md`.
- Do not use Python `assert` statements in source or tests. Raise a specific
  exception for an invalid runtime state. Use an explicit condition and
  `pytest.fail()` for a failed test expectation.
- Prefer early returns and continue statements to avoid unnecessary nesting.
  Use `yield from` for synchronous generator delegation. Async generators need
  ordinary yield loops. Use assignment expressions when they avoid a repeated
  lookup or calculation and keep the condition easy to read.
- Remove unused data and forwarding layers. Keep helpers that enforce a shared
  contract or express a useful domain operation.
- Preserve evidence-before-semantics ordering, awaited writes, checkpoint gates,
  and Scrapy JOBDIR callback serialization. See `docs/component-layout.md`.
- Write portable unit and business-contract tests that do not assume a host OS,
  absolute interpreter path, Python patch release, or external service. Label
  unavoidable OS security integration tests with linux_cgroup_v2 and keep
  their dedicated CI gate required; never silently skip their verification.
- Validate behavior with pytest, Scrapy contracts, and live LSP diagnostics for
  both `message_ingest/` and `tests/`. Use local Graph fixtures for integration tests.
