# Security Policy

Security is important to FinAssistBH and the
`dinohatibovic/EU_Funds_and_Grants_AI` repository.

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 2.2.x   | Yes       |
| < 2.2   | No        |

Please verify that a suspected vulnerability is reproducible on the latest
supported release or the current `main` branch.

## Reporting a Vulnerability

Do not report suspected security vulnerabilities through public GitHub issues,
discussions, pull requests, commit comments, or social media.

Use one of these private channels:

1. GitHub Private Vulnerability Reporting, when enabled for this repository.
2. Email the project owner:

```text
Dino Hatibović
GitHub: @dinohatibovic
Email: holdin.genesis@gmail.com
```

Suggested subject:

```text
[SECURITY] FinAssistBH vulnerability report
```

Do not include credentials, API keys, access tokens, personal data, database
contents, or other unnecessary sensitive information in the initial message.

## What to Include

Provide as much of the following information as possible:

- vulnerability type and affected component;
- affected release, branch, tag, or commit SHA;
- affected endpoint, file, function, dependency, workflow, or configuration;
- required environment and configuration;
- clear reproduction steps;
- minimal proof of concept, when safe;
- potential security impact;
- required authentication or privileges;
- suggested mitigation, if known;
- disclosure of automated or AI-assisted tools used during discovery.

Automated findings must be manually reviewed and reproduced before submission.

## Response Process

The project will aim to:

1. acknowledge receipt within 72 hours;
2. review reproducibility and request missing information;
3. classify the report as accepted, declined, duplicate, or out of scope;
4. provide weekly updates while an accepted report remains unresolved;
5. coordinate publication after a fix or suitable mitigation is available.

Resolution time depends on severity, reproducibility, complexity, dependency
availability, and deployment risk.

## Coordinated Disclosure

Keep vulnerability details private until a fix or mitigation is available, or
until a disclosure date has been agreed with the project owner.

Do not publicly disclose exploitation instructions, proof-of-concept code,
credentials, sensitive data, or production details before coordinated
publication.

## Responsible Testing

Do not:

- access, modify, or delete another user's data;
- retrieve more data than necessary to demonstrate the issue;
- perform denial-of-service, stress, or load testing;
- disrupt production or connected services;
- establish persistence;
- reuse discovered credentials or access tokens.

Stop testing immediately if sensitive data, credentials, or unauthorized
access are encountered, and report the finding privately.

## Security Updates

Security fixes may be communicated through:

- GitHub Security Advisories;
- supported releases;
- `CHANGELOG.md`;
- dependency updates;
- repository security notices.

## Recognition and Rewards

Accepted reports may be acknowledged with the reporter's permission.

FinAssistBH does not currently promise a bug-bounty payment or financial
reward.

Thank you for reporting security issues responsibly.
