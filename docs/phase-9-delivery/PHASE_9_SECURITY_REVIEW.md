# Phase 9 security review

## Result

The Phase 9 Technical Preview preserves the local-first boundary under synthetic
current-platform acceptance. It is not a penetration test, code-signing attestation,
or production certification.

## Verified controls

- Engine binds only to loopback and every non-handshake API requires a per-launch
  memory-only bearer token.
- Desktop supervises one owned engine; second-instance and explicit-Quit behavior
  produced zero orphan processes.
- Reconnect and relocate resolve project identity before changing a stored root.
  Mismatch stops the operation, and neither operation moves or edits source.
- Tray labels contain aliases/status only, not full paths, source, or evidence.
- Notification activation accepts only allowlisted route kinds and local stable IDs;
  forged, malformed, stale, and unavailable entity routes fail closed.
- Diagnostic copy data and support bundles are bounded and redact secret canaries,
  full home paths, tokens, authorization values, cookies, credentials, and keys.
- Support bundles contain no source/evidence bytes or arbitrary environment dump.
- The local updater validator accepts the correct signature and rejects tamper,
  wrong key, and incomplete content. Its private key is ephemeral and unpersisted.
- Production updater key/configuration is unchanged and signature enforcement remains
  mandatory.
- Package scan found no real project, local database, user path, private updater key,
  session token, support output, or repair workspace.
- All package validators used isolated synthetic source and no external network.
- Source-sensitive runtimes remain argv-only, no-shell, project-confined, bounded,
  and loopback-only by default.
- Safe Apply remains candidate-, project-, source-, journal-, nonce-, snapshot-, and
  fresh-verification-bound. Phase 9 adds no automatic Apply path.

## Threat boundaries retained

- No model/provider SDK, prompt harvesting, provider credential access, cloud sync,
  account, analytics/usage uploader, remote support transport, or APC dependency.
- No automatic Git push, commit, source repair, deployment, historical restore, or
  three-way merge.
- No real project acceptance was attempted by automation.
- Native notification visual/click behavior is not claimed without OS-level evidence.
- An unsigned local package has no publisher authenticity or Gatekeeper trust.

## Follow-up blockers

- platform-native signing and notarization;
- native acceptance on Apple Silicon, Windows, and Linux;
- production signed update delivery from an immutable public tag;
- an operator-approved disposable-copy real-project acceptance run;
- periodic dependency/licensing and support-bundle redaction review.
