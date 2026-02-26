# Security Policy

## Supported Versions

| Version | Supported          |
|---|---|
| 1.2.x   | ✅ Actively supported |
| 1.1.x   | ⚠️ Security fixes only |
| < 1.1   | ❌ Not supported |

## Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security vulnerabilities.**

Instead, report them privately by emailing: **security@greenflow-ai.dev**

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You will receive a response within **48 hours**.

## Security Best Practices

When running GreenFlow AI, please ensure:

1. **Never commit secrets** — keep `.env` out of version control (it's in `.gitignore`)
2. **Rotate API keys** regularly via your OpenAI dashboard
3. **Use strong SECRET_KEY** — at least 32 random characters
4. **Enable HTTPS** in production behind a reverse proxy (nginx/caddy)
5. **Restrict CORS origins** — update `ALLOWED_ORIGINS` in `.env` to your exact domain
6. **Use PostgreSQL** in production — SQLite is for development only
7. **Set `APP_DEBUG=false`** in production to hide stack traces
