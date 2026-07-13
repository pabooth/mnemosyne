# Releasing

Releases are performed by a maintainer and follow
[Semantic Versioning](https://semver.org/).

## Prepare the release

1. Ensure `main` is current and all required checks pass.
2. Move relevant entries from `CHANGELOG.md`'s `Unreleased` section into a
   section named `## [X.Y.Z] - YYYY-MM-DD`.
3. Update `VERSION`, `mnemo-core/pyproject.toml`,
   `mnemo-curator/pyproject.toml`, `mnemo-ui/package.json`, and
   `mnemo-ui/package-lock.json` to `X.Y.Z`.
4. Open and merge a release pull request.

After the release pull request is merged, update local `main`, create the tag,
and push it:

```bash
git switch main
git pull --ff-only
git tag vX.Y.Z
git push origin vX.Y.Z
```

Maintainers using the shared multi-repository workspace may instead use its
`bump-version.sh` helper to automate the version update, pull request, merge
wait, and tag creation.

## Publish the release

Pushing tag `vX.Y.Z` starts the release workflow. It:

- verifies the tag, manifests, lockfile, and changelog agree;
- runs core and UI checks;
- builds and smoke-tests Python distributions;
- builds source archives and container images;
- publishes versioned and `latest` container images to GHCR;
- creates a GitHub release using the changelog section as release notes.

Confirm that the GitHub release, archives, wheel, source distribution,
and container artifacts were published successfully.

PyPI publishing is not currently configured.
