# Releasing

Releases are fully automated with
[release-please](https://github.com/googleapis/release-please). Versions,
`CHANGELOG.md`, git tags, and GitHub Releases are derived from commit
messages — none are edited or run by hand.

This project is a local CLI (not published to PyPI or npm). A release is the
git tag + GitHub Release notes only.

## Flow

1. A branch is created and changes are committed.
2. A PR is opened with a **Conventional Commit title**. The title determines the
   next version when the PR is squash-merged into `main`:

   | PR title prefix | Example | Version bump |
   |---|---|---|
   | `fix:` | `fix: handle offline device timeout` | patch (1.1.0 → 1.1.1) |
   | `feat:` | `feat: add group volume command` | minor (1.1.0 → 1.2.0) |
   | `feat!:` / `fix!:` or a `BREAKING CHANGE:` footer | `feat!: require Python 3.12` | major (1.1.0 → 2.0.0) |
   | `chore:`, `docs:`, `refactor:`, `test:`, `ci:` | `docs: fix typo` | no release |

3. The **Tests** workflow runs on the PR. The PR is squash-merged to `main`.
4. **release-please** opens or updates a **Release PR** titled
   `chore(main): release X.Y.Z`. It bumps the version in `pyproject.toml`,
   `constants.py`, and `.release-please-manifest.json`, and appends to
   `CHANGELOG.md`. Multiple code PRs merged before a release are batched into
   one Release PR.
5. Merging the Release PR triggers `release.yml` again, which:
   - creates the `vX.Y.Z` git tag,
   - publishes a GitHub Release with the changelog notes.

A release therefore reduces to: merge the code PR(s), then merge the Release PR.

## Branch protection

`main` should stay compatible with this flow:

- **Require a pull request before merging** (0 required approvals is fine for a
  solo maintainer).
- **Block force-pushes and deletions.**
- **No required status checks on the Release PR.** GitHub does not trigger
  workflows for PRs opened by the built-in `GITHUB_TOKEN` (loop prevention), so
  a required check would leave every Release PR permanently unmergeable. Code
  PRs still run Tests; review those before merging.

### Actions permission (required once)

Under **Settings → Actions → General → Workflow permissions**:

1. **Read and write permissions**
2. **Allow GitHub Actions to create and approve pull requests**

Without (2), release-please can update its branch but cannot open the Release PR
(`GitHub Actions is not permitted to create or approve pull requests`).

## Notes

- **PR titles drive releases.** With squash merges, the PR title becomes the
  commit release-please reads. `chore:` / `docs:` / `ci:` titles intentionally
  produce no release.
- **Version source of truth** is `.release-please-manifest.json`.
  `pyproject.toml` and `constants.__version__` are kept in sync — do not
  hand-edit them for routine releases.
- Behavior is configured in `release-please-config.json`.

## Manual fallback

Manual tagging bypasses changelog automation and manifest sync. Prefer the
Release PR flow. If unavoidable:

```bash
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
gh release create vX.Y.Z --generate-notes
```
