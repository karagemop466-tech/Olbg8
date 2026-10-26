# Coordination

Session: `7fbe3ee0` · Branch: `arena/7fbe3ee0-olbg8` (platform-required; no alternate branch/worktree).

| Task | Status | Owner | File scope |
|---|---|---|---|
| Initial repository and access audit | in progress | 7fbe3ee0 | COORDINATION.md, README.md |
| Source registry, evidence policy, sport pricing research | in progress | 7fbe3ee0 | data/, docs/ |
| Collection, validation, rendering and tests | in progress | 7fbe3ee0 | scripts/, tests/, package.json, package-lock.json, .gitignore |
| Final integration, dashboard and publishing | in progress | 7fbe3ee0 | index.html, assets/, sports/, review/, methodology/, .github/ |

## Log
- 2026-10-26: Repository contains only README.md. No other task claims exist. Session claims the scopes above. All site/navigation integration belongs to this session.
- GitHub Pages is configured to deploy `main` root: https://karagemop466-tech.github.io/Olbg8/ (GitHub Pages API checked).
- Direct HTTPS request to https://www.olbg.com/betting-tips failed with SSL_ERROR_SYSCALL. Restricted outbound hosts may prevent collection; will test available retrieval tools. This is not evidence that OLBG has no events.
- Publication policy: no invented events, lines, statistics, injuries, confidence, predictions, or success claims. Blocked fields stay blank and are flagged; source directory links are not fixture verification.

## Progress — implementation checkpoint
- 2026-10-26, 7fbe3ee0: Initial branch did not exist on origin. First `pull --rebase` of that name failed; rebased on origin/main and immediately pushed the claim to the required session branch. No conflicting work found.
- Source audit: inspected 16 OLBG category pages (15 requested categories, Gaelic Football + Hurling) and primary official destinations for all 15 sports. 116 literal event observations retained. This is a partial extract, not all matches. Exact scope and exceptions: `docs/AUDIT.md`, `data/audit.json`, row-level `official_fact`/`flags`.
- 31 local tests pass: math kernels, true draw/push separation, odds boundaries, event IDs, withholding, source-link presence on table rows, 21-page static build and local links/fragments under `/Olbg8/`.
- Production pricing, calibration, complete official-history ingestion, event matching and prediction writing remain **needs review**, not done. No published picks and no fabricated lines. All gaps are on the site's Flagged for Review / Pricing pages.
- New public collector is fail-closed on robots.txt and access challenges. Sandbox attempt blocked at TLS; best-effort hosted discovery will be exercised after integration. It is not a daily prediction pipeline.
- Ownership scopes remain unchanged; integration by this session only. Repository branch is fixed by the platform, superseding requested session branch names.

## Concurrent-publication handoff
- Remote main advanced during this session with root dashboard owner `53f44a7c` and supplementary `arena-352da32b`. Read their combined task board on origin/main before integration. Preserve all their files byte-for-byte.
- This session relocates its distinct 116-entry inventory, field-scoped official corroboration, pricing kernels, tests, source audit and UI to **`evidence-lab/` only**, with uniquely named `.github/workflows/evidence-lab.yml` and `evidence-discovery.yml`. Root README, existing workflows and tooling are not owned by this session anymore.
- Request to root integration owner: optionally link `evidence-lab/index.html` from the root navigation after reviewing this supplementary scope; no root UI edits made by this session.
- Preserve current legacy main/root Pages configuration (another session recorded API update HTTP 403). Generated lab pages will be checked into evidence-lab/ and served under the existing site. Scheduled public discovery remains an artifact-only workflow; it does not commit to main or claim to refresh the public snapshot.
