# Browser Automation Usage Guide

Automated browser tool for extracting arXiv author endorsement data.

## Setup

```bash
# Install dependencies
uv sync
uv run playwright install chromium

# Configure credentials in .env
echo "ARXIV_USER=your_username" > .env
echo "ARXIV_PASS=your_password" >> .env

# Authenticate once
uv run python scripts/arxiv_auth_manager.py --login --verify
```

## Usage

### Check system status

```bash
uv run python scripts/status.py
```

### Check papers

```bash
uv run python scripts/arxiv_endorsement_browser.py \
  --paper-ids "2307.09288,2106.09685,2010.11929" \
  --export-json results.json
```

## Parameters

| Flag | Description | Required |
|------|-------------|----------|
| `--paper-ids` | Comma-separated arXiv IDs | Yes |
| `--export-json` | Export to JSON file | No |

Credentials loaded automatically from `.env` file.

## Authentication

Authentication state saved to `~/.arxiv_reviewer_cache/arxiv_auth_state.json` after first login. All subsequent runs reuse this session.

### Verify authentication

```bash
uv run python scripts/arxiv_auth_manager.py --verify
```

### Force fresh login

```bash
uv run python scripts/arxiv_auth_manager.py --login
```

### Clear saved authentication

```bash
uv run python scripts/arxiv_auth_manager.py --clear
```

## Output

Results saved to:
- Terminal: Progress and summary
- JSON: Export file if `--export-json` specified

JSON format:
```json
[
  {
    "arxiv_id": "2307.09288",
    "authors": ["Author 1", "Author 2"],
    "endorsers": ["Author 1"],
    "check_timestamp": "2025-12-09T20:30:00Z",
    "error": null
  }
]
```

## Rate Limiting

Hardcoded 30 seconds between papers (~120 papers/hour).

## Troubleshooting

**"Authentication expired"**
```bash
uv run python scripts/arxiv_auth_manager.py --login
```

**"ARXIV credentials not found"**
- Check `.env` exists with `ARXIV_USER` and `ARXIV_PASS`

**"Playwright not found"**
```bash
uv sync
uv run playwright install chromium
```
