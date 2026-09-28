---
{"description":"Prepare, publish, or repair a software release and write its release notes. Use for cutting a versioned release or editing release notes. NOT for updating an installed package, publishing articles, or discussing a release; for general documentation use documenting-code.","name":"releasing-code"}
---
<!-- Codex platform guidance -->
<!-- Use this platform's installed tool names exactly for shell, file reads, and search. If a referenced helper or optional tool is unavailable, say so and continue with built-in tools. -->


# Releasing Code

Prepare a release, route its publication, write its notes, or repair notes on a published release. Read [notes.md](references/notes.md) when writing or checking release content. Follow the project's own release instructions where they are more specific.

## Safety rules

- Publishing and repair change external state. Before any external mutation, get explicit user authorization for the exact repository, tag, and action. Skill routing, a tool approval, a passing check, or workflow ownership is not authorization.
- When a workflow owns the GitHub release, use that workflow's supported trigger. Do not publish around it with the CLI.
- Never overwrite package versions, move an existing local or published tag, force-push, or add `--clobber`.
- If the publisher, repository policy, a multi-step publication path, or the prior publication state is unclear, stop and ask.

## Prepare

Done when the notes pass the checker, the full staged release diff is reviewed, and the project's release validation passes. Commit, tag, or publish only after the notes are reviewed.

- Identify the project, the intended version and tag, the last published release, and the publisher. Read the working tree, tags, recent commits, diffs, and release configuration; do not infer policy from a workflow filename.
- Take changes since the verified previous release from commit bodies and diffs. Keep only user-visible changes that shipped in this release.
- Use the committed changelog or other established release source as the single notes source. Do not write a separate body for the hosting service.
- For each declared breaking change, write an `Upgrade` section with the required action, when to take it (before or after upgrading), and the consequence of skipping it.

## Determine who publishes

Read the workflow steps and scripts for the operation that actually creates or updates the GitHub release. A tag workflow that only builds or uploads package artifacts does not own the GitHub release.

## Publish

1. Verify that the exact tag points to the intended release commit. Before resuming or skipping work, check whether a hosting release already exists and confirm its tag, exact title, and attached artifact identity. Do not overwrite an existing release to force progress.
2. If a workflow owns the release, trigger it and inspect its result.
3. If no workflow owns the release, use the CLI with an explicit repository, the verified tag, the exact tag as title, and the same reviewed notes file:

   ```bash
   gh release create "$TAG" --repo owner/name --verify-tag \
     --title "$TAG" --notes-file "$NOTES_FILE"
   ```

4. Audit the artifacts attached to the tagged release separately. An installed-package audit is not evidence that the release assets are correct.

## Repair notes only

1. Require an already-published release; refuse to repair a draft or prerelease. Verify that the tag and release identify the intended version and package or artifact identity. The current title may be wrong when title correction is part of the repair.
2. Select the notes source explicitly as a full commit SHA, not the immutable tag. Read only the changelog from that commit; version, package metadata, and assets still come from the tag. Regenerate the section and validate it. Change no versions, assets, or tags.
3. Before mutating, back up the current title, body, and publication state (draft, prerelease, and latest flags) somewhere durable.
4. Apply the repair through the owning workflow's repair path. With no workflow owner, use `gh release edit "$TAG" --repo owner/name --title "$TAG" --notes-file "$NOTES_FILE"`.
5. Read the release back and verify its tag, exact title, body, and assets. A successful command is not proof of the published result.

## Optional release guard

The packaged pre-tool `release-guard` hook runs only when `HOOK_RELEASE_GUARD=1`. It checks direct `gh release create` and `gh release edit` forms against the notes checker and permits read-only queries and `--dry-run`. It is not authorization and not a shell parser: wrappers, aliases, nested shells, scripts, and other publishers are outside its scope.
