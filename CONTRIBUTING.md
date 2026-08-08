# Contributing to TaiGeotrans

## Development setup

```bash
python -m pip install -e ".[dev,all]"
python -m pytest
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src
python -m build
python -m twine check dist/*
```

Do not commit `.env`, TGOS credentials, generated distributions, or virtual
environments. Add tests and update the README when changing the public API.

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), for example:

```text
feat(api): add reverse TWD97 transformation
fix(tgos): validate the QueryAddr response
docs(readme): document optional dependencies
ci: add PyPI trusted publishing workflow
```

## Release

1. Update the version in `pyproject.toml`; `taigeotrans.__version__` reads the
   installed package metadata from that single source.
2. Run the complete local checks.
3. Merge the release commit into `main`.
4. Create and push a matching tag, such as `v0.1.1`.

The release workflow verifies the tag, builds and checks the distributions,
publishes to PyPI with Trusted Publishing, and creates a GitHub Release.
Configure the PyPI trusted publisher for the `release` GitHub environment
before pushing the first release tag.
