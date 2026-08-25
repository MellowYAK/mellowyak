# Demo Lab Guide

Demo Lab is an explicit synthetic product tour. Choose **Try MellowYak with a Demo Project**, select a parent folder, and create the clearly labeled offline fixture. It uses Python standard-library source, no Git requirement, no Docker, no external database, and no external network.

Recommended walkthrough:

1. Create the demo and inspect its initial known-good state.
2. Inject the controlled checkout regression.
3. Create the bad candidate and observe validation failure and disabled Apply.
4. Reset/recreate, create the valid candidate, and inspect its required checks.
5. Apply the valid candidate and observe the new Safety Snapshot and fresh live verification.
6. Run the simulated post-Apply failure scenario and verify byte-equal rollback.
7. Reset the scenario.

Demo-only mutation buttons are guarded by a synthetic marker and never appear as general project actions.
