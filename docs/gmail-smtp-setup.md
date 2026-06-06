# Gmail SMTP Setup for Binocular Notifications

This guide walks through configuring Binocular to send firmware update notifications via Gmail's SMTP server.

## Step 1: Generate a Gmail App Password

Gmail no longer allows plain password authentication for third-party apps. You must generate an **App Password** — a 16-character token tied to your Google account.

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Sign in to your Google account
3. Under "Select app", choose **Mail**
4. Under "Select device", choose **Other** and enter `Binocular`
5. Click **Generate**
6. Copy the 16-character password shown (e.g., `xxxx xxxx xxxx xxxx`)

**Requirements**: 2-Step Verification must be enabled on your Google account. If it's not, enable it at [myaccount.google.com/signinoptions/two-step-verification](https://myaccount.google.com/signinoptions/two-step-verification) first.

## Step 2: Configure Binocular

Add these values to your `.env` file:

```dotenv
# Gmail SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SMTP_FROM=your-email@gmail.com
SMTP_USE_TLS=true
```

Replace `your-email@gmail.com` with your actual Gmail address and the password with the App Password from Step 1.

### Using Docker Secrets

If you prefer not to store the password in plain text in `.env`, use the `_FILE` convention:

```dotenv
SMTP_PASSWORD_FILE=/run/secrets/gmail_app_password
```

Then inject the secret in `compose.yaml`:

```yaml
secrets:
  gmail_app_password:
    file: ./gmail_app_password.txt
```

## Step 3: Verify

After starting Binocular, configure the notification channel in the UI:

1. Navigate to **Settings > Notifications**
2. Add an **Email** channel
3. Enter the recipient email address (can be the same Gmail address)
4. Click **Test** to send a test notification

Check your inbox — you should receive a test email from Binocular. If not, check the container logs:

```bash
docker compose logs binocular | grep -i smtp
```

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `535 5.7.8 Authentication failed` | Wrong password or using account password instead of App Password | Regenerate the App Password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) |
| `534 5.7.9 Application-specific password required` | 2-Step Verification not enabled | Enable 2SV at [myaccount.google.com/signinoptions/two-step-verification](https://myaccount.google.com/signinoptions/two-step-verification) |
| `Connection timed out` | Port 587 blocked by firewall | Try port 465 with `SMTP_USE_TLS=false` (SSL instead of STARTTLS) |
| Email goes to spam | Gmail sees self-sent mail as suspicious | Whitelist Binocular's sender address in Gmail filters |
| `SMTP_UNKNOWN` in activity log | SMTP env vars not loaded | Verify `.env` file is in the same directory as `compose.yaml` and `env_file` directive is correct |

## Rate Limits

Gmail's SMTP relay limits:
- **500 emails per day** for personal accounts
- **2,000 emails per day** for Google Workspace accounts

Binocular only sends notifications when a firmware update is detected, so you're unlikely to hit these limits under normal use.
