# Gitlab LogLady - Group Milestone Changelog Generator

Automated changelog generation from GitLab group milestones with Slack integration.

## Overview

Gitlab LogLady automates the process of generating changelogs from GitLab group milestones and publishing them to Slack. When a sprint milestone is completed, it collects all closed issues from configured repositories, organizes them by product based on repository URLs, and sends formatted changelogs to your team's Slack channels.

## Installation

### Prerequisites

- Python 3.9+
- GitLab account with API access
- Slack workspace with webhook configured

### Setup

1. Clone the repository:
```bash
cd /path/to/local_repository
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure the application:
```bash
cp config.ini.example config.ini
# Edit config.ini with your GitLab URL, tokens, and Slack webhook
```

## Usage

### Basic Usage

```bash
# Dry run (preview without publishing to Slack)
python generate_changelog.py --milestone "09/10/2025" --dry-run

# Generate and publish to Slack (default behavior)
python generate_changelog.py --milestone "09/10/2025"
```

### How It Works

When you run the command:

1. **Fetches closed issues** from the GitLab group milestone
2. **Extracts the year** from milestone dates (e.g., 2025)
3. **Appends to year file** `changelog_archive/2025.md`:
   - If milestone doesn't exist → adds it at the top
   - If milestone already exists → replaces the existing entry (no duplicates)
4. **Generates temporary file** `changelog.md` for Slack
5. **Publishes to Slack** (unless `--dry-run` is specified)


### Publish Existing Changelog File

```bash
python generate_changelog.py --milestone "09/10/2025" --publish-only
```

### Custom Output File

```bash
python generate_changelog.py --milestone "09/10/2025" --output my_changelog.md
```

## Example Output

```markdown
**Changelog - 09/10/2025** (2025-09-26 → 2025-10-16)

**Product1** (3 issues)
* Issue / lorem ipsum (repository#123) (label1, label2)
* Issue / lorem ipsum (repository#1) (label1, label2)
* Issue / lorem ipsum (repository#2) (label1, label2)

**Product2** (1 issue)
* Issue / lorem ipsum (repository#123) (label1, label2)

---
Total: 4 issues closed | Estimated: 42.0h (6d)
```

**Format details:**
- Issues sorted alphabetically within each product
- Format: `* Title (repository#123) (label1, label2)`
- Shows repository name with issue number
- No alias labels (labels starting with @)
- Time shown in both hours and working days (8h = 1d)

## Setup Steps

1. **Create .env**
   ```bash
   # Edit with your GitLab token and Slack webhook
   LOGLADY_GITLAB_TOKEN = ...
   SLACK_WEBHOOK_URL = ...
   ```

2. **Create Group Milestone**
   - Go to your gitlab > group > then milestone.
   - Click "New milestone"
   - Create milestone (e.g., "09/10/2025", "Sprint 42")

3. **Test Configuration**
   ```bash
   python generate_changelog.py --milestone "Your Milestone" --dry-run
   ```

4. **Deploy**
   - Use manually via command line
   - Or set up GitLab CI/CD pipeline (see `.gitlab-ci.yml`)

## GitLab CI/CD Pipeline

The project includes a `.gitlab-ci.yml` file for automated execution.
