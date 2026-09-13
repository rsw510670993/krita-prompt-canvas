# Contributing

1. Create a focused branch.
2. Keep the desktop package free of mandatory third-party runtime dependencies.
3. Keep the Krita plugin limited to Python modules bundled with Krita.
4. Add tests for protocol, parsing, validation, or path changes.
5. Run `python -m unittest discover -s tests -v` before opening a pull request.

Changes that broaden the SVG allowlist must include a security rationale.

