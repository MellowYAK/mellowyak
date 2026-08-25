# macOS performance report

The final side-by-side measurement used three disposable data roots per engine. Phase 10 onefile
startup runs were 29.103, 18.329 and 18.721 seconds (median 18.721). Phase 11M onedir runs were 1.895,
1.901 and 1.899 seconds (median 1.899) on this Intel host. The exact run list, package sizes and chunk
inventory are in `MACOS_ENGINE_STARTUP.json` and `MACOS_PERFORMANCE.json`.

The largest minified JavaScript chunk fell from 591.08 kB (153.93 kB gzip) to 199,175 bytes
(49,175 bytes gzip), removing the Vite advisory. Final three-sample idle means were 0.0% CPU and
107,470,848-byte RSS for the desktop, and 0.1% CPU and 119,672,832-byte RSS for the engine. These
are local observations, not universal benchmarks.
