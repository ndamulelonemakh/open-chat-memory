# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in `openchatmemory`, please report it privately:

1. **Do not** open a public GitHub issue
2. Email the maintainers or use GitHub's private vulnerability reporting feature
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We aim to respond within 48 hours and will work with you to understand and address the issue.

## Security Considerations

This package processes chat history exports from third-party services. Users should:

- Keep database credentials secure (use environment variables)
- Review chat exports before processing if they contain sensitive information
- Treat `docs/examples/` as public synthetic-only data; never commit real exports, user metadata, phone numbers, or hidden provider context
- Use database access controls to limit exposure
- Consider data retention policies for stored chat histories

## Disclosure Policy

Once a vulnerability is fixed:
- We'll release a patched version
- Credit the reporter (unless they prefer anonymity)
- Publish details after users have had time to upgrade
