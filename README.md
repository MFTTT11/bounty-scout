# bounty-scout

Lists open GitHub issues funded through Lightning Bounties, BountyHub or Algora and grades whether a pull request is worth it.

For each issue it checks, with the GitHub API only:

- **funding** — the comment that links the platform and who wrote it
- **competition** — open PRs in the repository that mention the issue number
- **merge proof** — a PR by someone other than the owner merged in the last 30 days

Verdicts: `ready` (funded, merge proof, no competing PR), `quiet_repo`, `crowded`. Always confirm the amount and payout terms on the platform page before starting.

```bash
GITHUB_TOKEN=... python3 -m bounty_scout
python3 -m bounty_scout --platform lightningbounties --json
python3 -m unittest discover -s tests
```

Standard library only.
