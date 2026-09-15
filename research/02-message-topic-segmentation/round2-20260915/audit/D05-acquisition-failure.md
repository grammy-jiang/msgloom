# D05 opportunistic acquisition result

D05 is *A Publicly Available Annotated Corpus for Supervised Email Summarization* (Ulrich, Murray, Carenini, 2008).

- A clean official AAAI PDF was discoverable through public web search.
- The Raspberry Pi acquisition attempt used the official `f.aaai.org` PDF URL once.
- `curl` exited **6**: `Could not resolve host: f.aaai.org`.
- No retry loop or mirror fallback was used.
- No local PDF bytes were acquired, so D05 is **not** part of the Round 2 corpus.
- This is an acquisition/network limitation, not evidence that the paper or literature is absent.
- G5-A remains opportunistic and does not block the targeted Round 2 corpus.
