# Phase 9 updater validation

## Disposable local signer result

`PHASE_9_UPDATER_VALIDATION.json` reports **VERIFIED_WORKING**. The validator created
an ephemeral signing identity, served metadata and artifacts over loopback only, and
left production configuration unchanged.

| Scenario | Exact result |
|---|---|
| Valid signature | accepted |
| Newer version | detected |
| Same version | no update |
| Lower version | existing installation preserved |
| Tampered artifact | rejected |
| Wrong public key | rejected |
| Interrupted/incomplete download | rejected |
| Private key persistence | false |
| External network | not used |
| Production configuration mutation | false |

The verifier uses the resolved `minisign-verify` 0.2.5 crate (MIT license) as a
development-only validation dependency. No new Python, JavaScript, or product runtime
dependency was introduced for this test.

## Production updater

Status: **IMPLEMENTED_NOT_RUNTIME_VERIFIED**.

The product updater retains HTTPS metadata, its committed public verification key,
and mandatory signature verification. This run did not create a higher signed public
GitHub Release, publish `latest.json`, use a production private key, or execute a
signed cross-version update. Consequently it does not claim end-to-end update
delivery, rollback through the updater, or platform installer activation.

## Public validation still required

1. build and platform-sign a higher version from an immutable tag;
2. sign its updater artifact with the protected updater key;
3. publish exact same-commit metadata and hashes;
4. update from the previously signed installed version on each platform;
5. validate download interruption, invalid signature, install restart, schema
   upgrade, data preservation, application relaunch, and rollback/recovery policy;
6. confirm no older/lower version replaces the current installation silently.
