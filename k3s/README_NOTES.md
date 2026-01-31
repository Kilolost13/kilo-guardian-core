Notification setup for GitHub Actions deploy

You can configure optional notifications when the Deploy workflow runs by adding repository secrets:

- `SLACK_WEBHOOK` — Incoming webhook URL for Slack (https://api.slack.com/messaging/webhooks). The workflow will post a short message with the repo/run number and link.
- `DISCORD_WEBHOOK` — Incoming webhook URL for Discord. The workflow will POST a small payload with the run link.

Set the secret(s) in GitHub: Settings → Secrets → Actions → New repository secret.

Security note: keep these webhook URLs private (store as secrets). If you use third-party notif integrations, consider limiting scope and rotating tokens periodically.
