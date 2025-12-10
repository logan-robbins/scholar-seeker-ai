# 🕵️ Scholar Seeker AI

> **Autonomous agent that navigates arXiv to identify eligible endorsers for your submissions.**

Scholar Seeker AI solves the "cold start" problem for new arXiv authors. It automates the process of finding eligible endorsers in specific categories (like `cs.AI`) by autonomously browsing recent papers and verifying author endorsement eligibility using real authenticated sessions.

## 🚀 Features

- **🤖 Full Browser Automation**: Uses Playwright to navigate arXiv just like a human user.
- **🔐 Secure Authentication**: Handles arXiv login flows and persists sessions securely.
- **⚡ End-to-End Discovery**:
  - Scans recent papers in your target category.
  - Checks specific "Which authors can endorse?" links.
  - Filters and reports eligible endorsers.
- **🛡️ Rate Limit Aware**: Built-in delays to respect arXiv's server load.

## 🛠️ Installation

This project uses `uv` for modern Python dependency management.

```bash
# Clone the repo
git clone https://github.com/logan-robbins/scholar-seeker-ai.git
cd scholar-seeker-ai

# Install dependencies
uv sync
uv run playwright install chromium
```

## ⚙️ Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Add your arXiv credentials to `.env`:
   ```bash
   ARXIV_USER=my_username
   ARXIV_PASS=my_password
   ```

## 🏃 Usage

Run the automated scout to find endorsers in `cs.AI` (or any other category):

```bash
# Find endorsers from the last 10 papers in cs.AI
# Recommended: Use --delay 15 to respect arXiv rate limits
uv run python scripts/run_endorser_search.py --category cs.AI --limit 10 --delay 15
```

### Options

- `--category`: arXiv category code (default: `cs.AI`)
- `--limit`: Number of papers to scan (default: `10`)
- `--headless`: Run browser in background (default: visible)
- `--output`: Output JSON file (default: `endorsers_report.json`)

## 📊 Output Example

```text
📄 Paper: 2512.07810
   Link: https://arxiv.org/abs/2512.07810
   ✅ Eligible Endorsers found: 2
      - Jordan Taylor
      - Satvik Golechha
```

## 📄 License

MIT © [Logan Robbins](https://github.com/logan-robbins)
