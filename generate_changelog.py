#!/usr/bin/env python3
"""Main script to generate and publish changelogs from GitLab milestones."""

import argparse
import configparser
import os
import sys
from datetime import datetime

from src.gitlab_client import GitLabClient
from src.changelog_generator import ChangelogGenerator
from src.slack_publisher import SlackPublisher


def load_config(config_path='config.ini'):
    """Load configuration from INI file."""
    config = configparser.ConfigParser()

    # Try to load from file
    if os.path.exists(config_path):
        config.read(config_path)
    else:
        print(f"Warning: Config file '{config_path}' not found")

    # Override with environment variables if present
    if 'GITLAB_URL' in os.environ:
        if 'gitlab' not in config:
            config['gitlab'] = {}
        config['gitlab']['url'] = os.environ['GITLAB_URL']

    if 'GITLAB_TOKEN' in os.environ:
        if 'gitlab' not in config:
            config['gitlab'] = {}
        config['gitlab']['token'] = os.environ['GITLAB_TOKEN']

    if 'GITLAB_GROUP_ID' in os.environ:
        if 'gitlab' not in config:
            config['gitlab'] = {}
        config['gitlab']['group_id'] = os.environ['GITLAB_GROUP_ID']

    if 'GITLAB_PROJECT_ID' in os.environ:
        if 'gitlab' not in config:
            config['gitlab'] = {}
        config['gitlab']['project_id'] = os.environ['GITLAB_PROJECT_ID']

    if 'SLACK_WEBHOOK_URL' in os.environ:
        if 'slack' not in config:
            config['slack'] = {}
        config['slack']['webhook_url'] = os.environ['SLACK_WEBHOOK_URL']

    if 'SLACK_CHANNEL' in os.environ:
        if 'slack' not in config:
            config['slack'] = {}
        config['slack']['channel'] = os.environ['SLACK_CHANNEL']

    return config


def parse_repository_mapping(config):
    """Parse repository mapping from config."""
    if 'repositories' not in config:
        print("Error: Missing [repositories] section in config")
        return None

    # Parse from config
    repository_mapping = {}
    for product, repos_str in config['repositories'].items():
        repos = [r.strip() for r in repos_str.split(',')]
        repository_mapping[product] = repos

    return repository_mapping


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Generate changelog from GitLab milestone and publish to Slack'
    )
    parser.add_argument(
        '--milestone',
        required=True,
        help='Milestone name or ID'
    )
    parser.add_argument(
        '--config',
        default='config.ini',
        help='Path to config file (default: config.ini)'
    )
    parser.add_argument(
        '--output',
        default='changelog.md',
        help='Output markdown file (default: changelog.md)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Generate changelog but do not publish to Slack'
    )
    parser.add_argument(
        '--publish-only',
        action='store_true',
        help='Only publish existing changelog file to Slack'
    )
    parser.add_argument(
        '--archive-dir',
        default='changelog_archive',
        help='Directory for year-based changelog files (default: changelog_archive)'
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Validate configuration
    if 'gitlab' not in config:
        print("Error: Missing [gitlab] section in config")
        return 1

    if 'url' not in config['gitlab']:
        print("Error: Missing gitlab.url in config")
        return 1

    if 'token' not in config['gitlab']:
        print("Error: Missing gitlab.token in config")
        return 1

    if 'group_id' not in config['gitlab']:
        print("Error: Missing gitlab.group_id in config")
        return 1

    if not args.publish_only:
        # Initialize GitLab client
        print("Connecting to GitLab...")
        gitlab_client = GitLabClient(
            url=config['gitlab']['url'],
            token=config['gitlab']['token'],
            group_id=config['gitlab']['group_id']
        )

        # Test connection
        if not gitlab_client.test_connection():
            print("Error: Failed to connect to GitLab")
            return 1

        # Get milestone
        print(f"Fetching milestone: {args.milestone}")

        # Try to get milestone by name first, then by ID
        try:
            milestone_id = int(args.milestone)
            milestone = gitlab_client.get_milestone_by_id(milestone_id)
        except ValueError:
            milestone = gitlab_client.get_milestone_by_name(args.milestone)

        if not milestone:
            print(f"Error: Milestone '{args.milestone}' not found")
            return 1

        print(f"Found milestone: {milestone.title} (ID: {milestone.id})")

        # Parse repository mapping
        repository_mapping = parse_repository_mapping(config)
        if not repository_mapping:
            return 1

        # Get all project URLs from repository mapping
        project_urls = []
        for repos in repository_mapping.values():
            project_urls.extend(repos)

        # Get closed issues
        print("Fetching closed issues...")
        print(f"Filtering issues from {len(project_urls)} repositories...")
        issues = gitlab_client.get_closed_issues(milestone.title, project_urls)

        print(f"Found {len(issues)} closed issues")

        if len(issues) == 0:
            print("Warning: No closed issues found in this milestone")

        # Generate changelog
        print("Generating changelog...")
        generator = ChangelogGenerator(repository_mapping)

        # Parse dates
        start_date = datetime.fromisoformat(milestone.start_date) if milestone.start_date else None
        due_date = datetime.fromisoformat(milestone.due_date) if milestone.due_date else None

        # Append to year-based changelog file (e.g., 2025.md)
        # Automatically prevents duplicates and organizes by year
        generator.append_to_year_changelog(
            milestone_name=milestone.title,
            milestone_dates=(start_date, due_date),
            issues=issues,
            archive_dir=args.archive_dir
        )

        # Generate temporary file for Slack publishing
        generator.generate_markdown_file(
            milestone_name=milestone.title,
            milestone_dates=(start_date, due_date),
            issues=issues,
            output_file=args.output
        )
        print(f"Temporary changelog for Slack: {args.output}")

    # Publish to Slack
    if 'slack' in config and 'webhook_url' in config['slack']:
        print("Publishing to Slack...")

        channel = config['slack'].get('channel', None)
        publisher = SlackPublisher(
            webhook_url=config['slack']['webhook_url'],
            channel=channel
        )

        success = publisher.publish_from_file(args.output, dry_run=args.dry_run)

        if success:
            print("Done!")
            return 0
        else:
            print("Error: Failed to publish to Slack")
            return 1
    else:
        print("Warning: Slack configuration not found, skipping publish")
        print(f"Changelog available in: {args.output}")
        return 0


if __name__ == '__main__':
    sys.exit(main())
