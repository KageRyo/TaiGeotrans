# Security policy

## Credentials

Never commit TGOS AppID/APIKey values or place them in GitHub Actions logs.
Use local environment variables or the repository's ignored `.env` file.
If a credential is exposed, revoke it and issue a replacement through TGOS.

## Reporting a vulnerability

Please do not open a public issue for a security vulnerability. Use GitHub's
private vulnerability reporting on the repository's Security tab, or contact
the maintainer privately with reproduction steps, impact, and affected versions.
