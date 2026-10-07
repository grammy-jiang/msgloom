# Topic 02 Academic Round 2 acquisition notes

- Manual discovery preceded download.
- Clean public/canonical sources only.
- Same-provider ACL PDF requests were spaced by at least 31 seconds.
- No download retry loops were used.
- Bibliographic identity and byte integrity were checked separately.
- All six acquired PDFs passed PDF-magic, title, author, page-count, SHA-256, and extraction sanity checks.
- No acquired Round 2 PDF duplicates a Round 1 PDF by SHA-256.
- D05 failed local DNS acquisition and remains pending; web discoverability is not counted as corpus acquisition.
