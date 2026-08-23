# Open-source license decision required

No license file existed at the clean Phase 1 starting commit. Phase 1 therefore does not add or imply a license. Copyright law applies until the owner makes a documented choice; public source visibility alone does not grant reuse rights. This is an engineering comparison, not legal advice or formal clearance.

| Option | Practical effect | Considerations for MellowYak |
|---|---|---|
| Apache-2.0 | Permissive use with notices and an express patent grant. | Strong ecosystem clarity; more notice obligations than MIT. |
| MIT | Short permissive license with broad reuse. | Simple adoption; no explicit patent grant and permits closed derivatives. |
| MPL-2.0 | File-level copyleft. Modified covered files stay open while larger works may remain separate. | Can protect core improvements while remaining connector-friendly; boundary management matters. |
| AGPL-3.0 | Strong copyleft including network interaction. | Protects hosted modifications, but may reduce commercial/enterprise adoption and complicate integrations. |
| Open core | Governance/business model, not itself a license. Core and proprietary modules need explicit boundaries and compatible licenses. | Could fund connectors/team features, but risks confusing the privacy/open-source promise unless defined transparently. |

The owner should obtain appropriate legal advice and select a license before accepting external contributions or distributing release packages. Signing a contributor agreement or adding licensing enforcement is outside Phase 1.
