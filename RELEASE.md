# Release process for logerr

This reflects how releases actually work today - trusted publishing is live,
there's no `.pypirc`/API token anywhere, and `pixi.toml` no longer exists as
a separate file (folded into `pyproject.toml`).

## How it works

1. **Bump the version** in two places (checked by `check-version-sync`):
   - `pyproject.toml`'s `[project] version`
   - `logerr/__init__.py`'s `__version__`
2. **Update `CHANGELOG.md`**: move the `[Unreleased]` section's contents
   under a new dated `## [X.Y.Z] - YYYY-MM-DD` heading.
3. **Verify locally**:
   ```bash
   pixi run -e dev check-all   # tests + quality + version-sync
   ```
4. **Commit and push to `main`.**
5. **Tag and push**:
   ```bash
   git tag -a vX.Y.Z -m "logerr X.Y.Z"
   git push origin vX.Y.Z
   ```
   Pushing the tag automatically builds the package and publishes it to
   **TestPyPI** (`.github/workflows/publish.yml`, triggered by `v*` tags).
   This is cheap and fully reversible - TestPyPI is a scratch index, so no
   human checkpoint is needed for it.
6. **Sanity-check the TestPyPI upload**:
   ```bash
   pip install -i https://test.pypi.org/simple/ logerr==X.Y.Z
   ```
7. **Publish to real PyPI manually**: GitHub → Actions → *Publish to PyPI*
   → *Run workflow* → choose `pypi`. This step is **never** automatic - a
   published version number on real PyPI can never be reused, unlike a git
   tag (delete and re-push) or a TestPyPI upload (scratch index), so it
   stays behind a deliberate human trigger.

## Trusted publishing (no tokens)

Both `publish-testpypi` and `publish-pypi` jobs use PyPI's OIDC trusted
publishing (`permissions: id-token: write` + `pypa/gh-action-pypi-publish`)
rather than an API token. This was configured once, by hand, at
https://pypi.org/manage/account/publishing/ and
https://test.pypi.org/manage/account/publishing/ - Owner `jesserobertson`,
Repo `logerr`, Workflow `publish.yml`, Environment `pypi` (and `testpypi`
for the TestPyPI side). If publishing ever needs re-registering (new repo
name, moved workflow file, etc.), that page is where it happens - there is
no secret to rotate.

## CI, on every push/PR

`.github/workflows/ci.yml` runs quality checks, the full test matrix
(ubuntu/macos/windows + a Python 3.13 leg), and uploads coverage + test
results to Codecov (`CODECOV_TOKEN` secret - required even for public repos
now, Codecov's tokenless upload policy changed). Codecov tokens are
per-repo: if coverage stops showing up on
https://app.codecov.io/github/jesserobertson/logerr, the first thing to
check is whether `CODECOV_TOKEN` in this repo's secrets actually holds
*this* repo's token and not another repo's (the upload log line "results
will be available at: https://app.codecov.io/github/<owner>/<repo>/commit/..."
tells you which project a given run actually landed under).

## Version support policy

Pre-1.0: breaking changes may land in a minor version bump per
`CHANGELOG.md`'s stated policy. There's no LTS/backport branch - only
`main` and its latest tag are supported.
