# macOS Acceptance Lab guide

The lab is a permanently marked synthetic polyglot fixture under
`fixtures/macos_acceptance_lab`. Validation copies it into a temporary directory and never registers
the source fixture in place.

It supplies three local runtime profiles: a Python loopback Web/API service, a CLI operation and a
test command. Static HTML/JavaScript uses English and Hebrew translation catalogs; Hebrew selects
RTL. There are no external dependencies, credentials, database, Docker or network services.

Run the validator with the packaged engine:

```sh
python3 scripts/validate_macos_acceptance_lab.py \
  --engine <packaged-engine> \
  --fixture fixtures/macos_acceptance_lab \
  --output <report.json>
```

The marker gate rejects an unmarked directory, proving test-only actions cannot be applied to an
ordinary real project. Phase 8 packaged acceptance remains the full production-service proof for
Known Good, WATCH, repeated comparable failure, isolated candidate validation, explicit Apply,
byte-identical rollback and four crash points.
