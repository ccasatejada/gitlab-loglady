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

## Configuration

### Config File (config.ini)

Create `config.ini` from the example file

### Product to Repository Mapping

### Environment Variables

You can also use environment variables (they override config.ini):

```bash
export GITLAB_URL=""
export GITLAB_TOKEN=""
export GITLAB_GROUP_ID=""
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
export SLACK_CHANNEL="#changelog"
```

### GitLab Token Permissions

Your GitLab token needs the following scopes:
- `api` (full API access) or
- `read_api` + `read_repository` (minimum required)

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

### Custom Archive Directory

```bash
python generate_changelog.py --milestone "09/10/2025" --archive-dir /path/to/archive
```

### Use Milestone ID Instead of Name

```bash
python generate_changelog.py --milestone 680
```

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

1. **Create config.ini**
   ```bash
   cp config.ini.example config.ini
   # Edit with your GitLab token and Slack webhook
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

### Pipeline Jobs

1. **test_connection**: Verify GitLab API connection
2. **generate_changelog**: Generate changelog and save as artifact
3. **publish_to_slack**: Publish previously generated changelog
4. **generate_and_publish**: Combined job (generate + publish)

### Setting Up CI/CD

1. Add the following CI/CD variables in your GitLab project settings:
   - `GITLAB_TOKEN`: Your GitLab API token
   - `SLACK_WEBHOOK_URL`: Your Slack webhook URL
   - `MILESTONE_NAME`: The milestone to process (or pass via pipeline trigger)

2. Push the project to GitLab

3. Trigger the pipeline manually from GitLab UI:
   - Go to CI/CD > Pipelines
   - Click "Run Pipeline"
   - Add variable `MILESTONE_NAME` with the milestone name
   - Run the `generate_and_publish` job

### Example Pipeline Trigger

```bash
curl -X POST \
  -F token=YOUR_TRIGGER_TOKEN \
  -F ref=main \
  -F "variables[MILESTONE_NAME]=09/10/2025" \
  https://{gitlab-url}/api/v4/projects/PROJECT_ID/trigger/pipeline
```

## Changelog Archive Structure

The tool maintains year-based changelog files:

- **changelog_archive/**: Contains all changelogs organized by year

Example structure:
```
changelog_archive/
├── 2025.md     # All 2025 milestones (newest at top)
├── 2024.md     # All 2024 milestones
└── 2023.md     # All 2023 milestones
```

Each year file contains all milestones for that year with the newest entries at the top. Running the same milestone again will update the existing entry instead of creating a duplicate.

## Troubleshooting

### GitLab API Connection Failed

- Verify your `GITLAB_TOKEN` has correct permissions (`read_api` scope)
- Check that `GITLAB_URL` and `GITLAB_GROUP_ID` are correct
- Test connection: Run `debug_milestone.py` to diagnose issues

### Milestone Not Found

- Check milestone name spelling (case-sensitive)
- Try using milestone ID instead of name
- Verify milestone exists in the group (not just in a single project)
- Run `debug_milestone.py` to see all available milestones

### No Issues Found

- Verify issues are marked as "closed"
- Check milestone assignment (issues must be assigned to the group milestone)
- Ensure repositories are listed in `[repositories]` section
- **Important:** GitLab API for group milestones requires milestone **title** (not ID)
- Run with `--dry-run` to see what would be generated

### Issues in "Uncategorized"

- Add the repository to appropriate product in config
- Verify repository URL matches exactly (check trailing slashes)
- Run `debug_milestone.py` to see which repositories have issues

### Slack Webhook Not Working

- Verify webhook URL is correct and active
- Check that the webhook has permission to post to the channel
- Test with curl: `curl -X POST -H 'Content-Type: application/json' -d '{"text":"Test"}' YOUR_WEBHOOK_URL`

### "Could not find project" warnings

- Check repository URL in config
- Verify your token has access to the repository
- Ensure the repository exists and is accessible

## Debugging

Use the included debug script to diagnose issues:

```bash
python debug_scripts/debug_milestone.py
```

This will:
- Test GitLab API connection
- List all available milestones
- Show issues from all projects for a specific milestone
- Identify which repositories are configured/missing
- Display issues grouped by product
