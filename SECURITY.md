# Security policy

Please do not open a public issue for a suspected vulnerability or exposed secret. Use GitHub's private vulnerability reporting for this repository.

This project does not require committed credentials. BigQuery uses Application Default Credentials, and webhook URLs must be supplied through environment variables. If a credential is committed accidentally, revoke it before removing it from Git history.

Only the latest version on the `main` branch receives security fixes.
