#!/usr/bin/env python3
"""Main script to generate and publish changelogs from GitLab milestones."""

import argparse
import sys
from datetime import datetime

from src import config
from src.changelog_generator import ChangelogGenerator
from src.gitlab_client import GitLabClient
from src.slack_publisher import SlackPublisher

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

    if not args.publish_only:
        # Initialize GitLab client
        print("Connecting to GitLab...")
        gitlab_client = GitLabClient(
            url=config.GITLAB_URL,
            token=config.GITLAB_TOKEN,
            group_id=config.GITLAB_GROUP_ID
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

        # Get all project URLs from repository mapping
        project_urls, repos_to_products = config.get_repositories()

        # Get closed issues
        print("Fetching closed issues...")
        print(f"Filtering issues from {len(project_urls)} repositories...")
        issues = gitlab_client.get_closed_issues(milestone.title, project_urls)

        print(f"Found {len(issues)} closed issues")

        if len(issues) == 0:
            print("Warning: No closed issues found in this milestone")

        # Generate changelog
        print("Generating changelog...")
        generator = ChangelogGenerator(repos_to_products)

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
    print("Publishing to Slack...")

    publisher = SlackPublisher(
        webhook_url=config.SLACK_WEBHOOK_URL,
        channel=config.SLACK_CHANNEL
    )
    success = publisher.publish_from_file(args.output, dry_run=args.dry_run)
    if success:
        print("Done!")
        return 0
    else:
        print("Error: Failed to publish to Slack")
        return 1


if __name__ == '__main__':
    sys.exit(main())
