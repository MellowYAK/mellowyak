# ADR-0012: Browser capture privacy

Date: 2026-08-24
Status: Accepted

## Decision

Capture records bounded meaningful events and normalized local metadata. It does not persist request/response bodies, headers, cookies, authorization, browser storage, mouse movement, raw keystrokes, or input values. Password/secret/token fields are masked for screenshots and normal input is redacted by default. Query values are removed from recorded URLs.

Defaults are 500 actions, 1,000 network observations, 30 screenshots, 10 MiB per artifact, and 250 MiB per accepted evidence design bundle. Video is off. Trace remains off unless package validation proves it for a platform. Users review evidence, may exclude steps/observations and delete review artifacts, and must attest explicitly before acceptance.

## Consequences

Screenshots can still contain project or user data, so the UI warns users and evidence remains local. Browser capture proves observed routes, APIs, and UI targets only; it does not prove backend function execution.
