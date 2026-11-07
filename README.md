# bounty-scout

Lists open GitHub issues funded through Lightning Bounties, BountyHub or Algora and grades whether a pull request is worth it.

For each issue it checks, with the GitHub API only:

- **funding** — the comment that links the platform and who wrote it
- **competition** — open PRs in the repository that mention the issue number
- **merge proof** — a PR by someone other than the owner merged in the last 30 days

Verdicts: `verified_ready` (funding comment by the platform's official bot such as `algora-pbc[bot]`, merge proof, no competing PR), `candidate` (only a platform link or missing proof — not verified), `crowded`. `verified_ready` also requires the anti-waste gate: a verified cash reward > 0, an issue opened in the last 21 days (or a maintainer confirming the bounty in the last 7 days), no competing PR and at most 2 other applicants. Results are ranked by proven payment × completability × low competition, not by the claimed amount. Always confirm the amount and payout terms on the platform page before starting.

```bash
GITHUB_TOKEN=... python3 -m bounty_scout
python3 -m bounty_scout --platform lightningbounties --json
python3 -m unittest discover -s tests
```

Standard library only.
