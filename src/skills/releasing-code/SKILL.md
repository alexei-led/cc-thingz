---
name: releasing-code
description: Prepare, publish, or repair a software release and write its release notes. Use for cutting a versioned release or editing release notes. NOT for updating an installed package, publishing articles, or discussing a release; for general documentation use documenting-code.
---

# Releasing Code

Own release preparation, publication routing, release-note writing, and notes-only repair. Read [notes.md](references/notes.md) when writing or checking release content.

## Prepare

1. Identify the project, intended version/tag, last published release, and current publisher. Inspect the working tree, tags, recent commits, diffs, and release configuration. Do not infer policy from a workflow filename.
2. Compare changes since the verified previous release. Check commit bodies and diffs; keep only user-visible changes that shipped in this release.
3. Use the project's committed changelog or other established release source as the single notes source. Do not create a separate, conflicting body for the hosting service.
4. Write concise notes and validate them with the packaged `scripts/release_notes.py` checker. The word budget is advisory; keep critical migration steps and known issues even when they exceed it.
5. For declared breaking changes, include an `Upgrade` section with the required action, before/after timing, and consequence of skipping it. Do not publish until this is clear.
6. Review the full staged release diff and run the project's release validation. Do not commit, tag, or publish before the notes are reviewed.

## Determine who publishes

Inspect workflow steps and scripts for the actual GitHub-release creation/update operation. A tag workflow that only builds or uploads package artifacts does not own the GitHub release. If ownership, repository policy, or a multi-step publication path is unknown, stop and ask; do not assume that a successful notes check authorizes publishing.

For cc-thingz, `.github/workflows/release.yml` is the only GitHub release publisher. A tag push creates the GitHub release. Notes-only repair uses the default-branch workflow with the existing tag and an explicitly selected full notes-source commit SHA. The workflow executes trusted default-branch code, reads only `CHANGELOG.md` from the selected commit, and uses package metadata from the tagged release. It rejects draft and prerelease targets, verifies tag/version and assets, preserves the prior title/body and publication-state flags in a linked 90-day artifact, permits title correction, and changes no assets. Do not run `gh release create` or `gh release edit` for cc-thingz.

For this repository, prepare with `scripts/release/release-tag prepare vX.Y.Z`, review and commit the version, generated, and changelog changes, then run `scripts/release/release-tag finalize vX.Y.Z` on the clean committed release. `finalize` reruns `make ci` and creates a local annotated tag; it does not push. Never overwrite package versions or move an existing local or published tag.

## Publish

Publishing changes external state. Before any external mutation, get explicit user authorization for the exact repository, tag, and action. Skill routing, a tool approval, a passing guard, or workflow ownership is not publication authorization.

1. Verify the exact tag points to the intended committed release. Check whether a hosting release already exists before resuming or skipping work; confirm its tag, exact title, and attached artifact identity. Do not overwrite an existing release to force progress.
2. If a GitHub workflow owns release creation, use that workflow's supported trigger and inspect its result. Do not publish around it with the CLI.
3. If no workflow owns the GitHub release, use the CLI only after approval and only with an explicit repository, verified tag, exact tag title, and the same reviewed notes file, for example:

   ```bash
   gh release create "$TAG" --repo owner/name --verify-tag \
     --title "$TAG" --notes-file "$NOTES_FILE"
   ```

4. Never add `--clobber`, force-push, or move a published tag. If identity or prior publication state is ambiguous, stop and ask.
5. Audit the release's tagged artifacts separately. An installed-package audit is not evidence that assets attached to the tagged release are correct.

## Repair notes only

1. Verify the existing tag and release identify the intended version and package/artifact identity. Require an already-published, non-draft, non-prerelease release. The current title may be wrong if title correction is part of the repair.
2. Select the committed notes source explicitly, regenerate the corrected section, and validate it. Do not change package versions, assets, or tags for a notes-only correction.
3. Before mutation, preserve the current title and body in a durable backup. For cc-thingz, pass the target tag and full notes-source commit SHA to the workflow repair path; it reads only `CHANGELOG.md` from that SHA and links the backup artifact in the run summary. For a repository with no workflow owner, `gh release edit "$TAG" --repo owner/name --title "$TAG" --notes-file "$NOTES_FILE"` is allowed only after explicit authorization.
4. Read the release again and verify its tag, exact title, body, and assets. Do not treat a successful command as proof of the published result.

## Optional release guard

The packaged pre-tool `release-guard` is disabled unless `HOOK_RELEASE_GUARD=1`. It checks a narrow set of direct `gh release create` and `gh release edit` forms against the shared notes checker. It permits read-only release queries and `--dry-run`. It is not an authorization mechanism or a complete shell parser. Wrappers, aliases, nested shells, substitutions, scripts, and other publishers are outside its scope; inspect project policy and stop on unknown or multi-step flows.
