# Security Policy

## Supported Versions

This project is under active early-stage development. Until a `1.0` release,
security fixes are applied only to the `main` branch.

| Version | Supported          |
| ------- | ------------------- |
| `main`  | :white_check_mark:  |
| others  | :x:                  |

## Reporting a Vulnerability

If you discover a security vulnerability, **please do not open a public GitHub
issue**. Instead, report it privately so it can be fixed before it's disclosed:

- Use GitHub's [private vulnerability reporting](../../security/advisories/new)
  for this repository, or
- Email the maintainers with a description of the issue, steps to reproduce,
  and its potential impact.

We aim to acknowledge reports within a few business days and to keep you
updated as the issue is investigated and fixed.

## Scope

Notable areas of interest for this project include:

- Handling of credentials and API tokens for connected data sources and CRM
  destinations (`SECRET_KEY`, `ENCRYPTION_KEY`, source passwords).
- Injection risks in dynamically constructed database queries or CRM API
  calls.
- Authentication/authorization on API endpoints.

Please avoid testing against production or third-party systems; use a local
or disposable environment when researching a report.
