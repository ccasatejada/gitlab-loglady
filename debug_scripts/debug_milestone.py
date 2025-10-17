#!/usr/bin/env python3
"""Debug script to check milestone and issues."""

import configparser
import sys
from src.gitlab_client import GitLabClient

def main():
    # Load config
    config = configparser.ConfigParser()
    config.read('config.ini')

    print("=" * 60)
    print("DEBUG: Milestone and Issues")
    print("=" * 60)

    # Initialize client
    client = GitLabClient(
        url=config['gitlab']['url'],
        token=config['gitlab']['token'],
        group_id=config['gitlab']['group_id']
    )

    # Test connection
    print("\n1. Testing connection...")
    if client.test_connection():
        print("   ✅ Connection successful!")
    else:
        print("   ❌ Connection failed!")
        return

    # List all milestones
    print("\n2. Available milestones in the group:")
    milestones = client.group.milestones.list(get_all=True)
    print(f"   Found {len(milestones)} milestones:")
    for m in milestones:
        state = "ACTIVE" if m.state == "active" else "CLOSED"
        print(f"   - '{m.title}' (ID: {m.id}, State: {state})")

    # Ask user for milestone
    print("\n3. Enter the milestone name exactly as shown above:")
    milestone_name = input("   Milestone name: ").strip()

    # Find milestone
    milestone = None
    for m in milestones:
        if m.title == milestone_name:
            milestone = m
            break

    if not milestone:
        print(f"\n   ❌ Milestone '{milestone_name}' not found!")
        print("   Please copy the exact name from the list above.")
        return

    print(f"\n   ✅ Found milestone: {milestone.title} (ID: {milestone.id})")
    print(f"   State: {milestone.state}")
    print(f"   Start: {milestone.start_date}")
    print(f"   Due: {milestone.due_date}")

    # Get all projects in group
    print("\n4. Getting projects in the group...")
    all_projects = client.get_projects_in_group()
    print(f"   Found {len(all_projects)} projects in the group")

    # Parse repository mapping
    print("\n5. Checking configured repositories...")
    from generate_changelog import parse_repository_mapping
    repository_mapping = parse_repository_mapping(config)

    all_repo_urls = []
    for product, repos in repository_mapping.items():
        all_repo_urls.extend(repos)

    print(f"   Configured {len(all_repo_urls)} repositories")

    # Get issues from ALL projects (not just configured ones)
    print("\n6. Fetching issues from ALL projects (checking all states)...")
    all_issues = []
    issue_states = {}

    for project in all_projects:
        try:
            # Fetch ALL issues for this milestone (any state)
            all_milestone_issues = project.issues.list(
                milestone=str(milestone.id),
                get_all=True
            )

            if all_milestone_issues:
                closed_count = 0
                open_count = 0

                for issue in all_milestone_issues:
                    if issue.state == 'closed':
                        closed_count += 1
                    else:
                        open_count += 1

                    all_issues.append({
                        'project_name': project.name,
                        'project_url': project.web_url,
                        'iid': issue.iid,
                        'title': issue.title,
                        'state': issue.state,
                        'labels': issue.labels
                    })

                    # Track states
                    issue_states[issue.state] = issue_states.get(issue.state, 0) + 1

                if closed_count > 0 or open_count > 0:
                    print(f"   - {project.name}: {closed_count} closed, {open_count} open")
        except Exception as e:
            # Skip projects we can't access
            pass

    print(f"\n   Total issues found across all projects: {len(all_issues)}")

    if issue_states:
        print("\n   Issue states summary:")
        for state, count in sorted(issue_states.items()):
            print(f"   - {state}: {count} issues")

    if all_issues:
        print("\n7. Issues by repository:")
        from collections import defaultdict
        issues_by_repo = defaultdict(list)
        for issue in all_issues:
            issues_by_repo[issue['project_name']].append(issue)

        for repo_name in sorted(issues_by_repo.keys()):
            issues = issues_by_repo[repo_name]
            repo_url = issues[0]['project_url']
            is_configured = repo_url in [r.rstrip('/') for r in all_repo_urls]
            status = "✅ CONFIGURED" if is_configured else "⚠️  NOT CONFIGURED"
            print(f"   - {repo_name} ({len(issues)} issues) {status}")
            print(f"     URL: {repo_url}")
            if not is_configured:
                print(f"     ⚠️  This repository is not in your config.ini!")

    # Now fetch with configured repos only
    print("\n8. Fetching issues from CONFIGURED repositories only...")
    configured_issues = client.get_closed_issues(milestone.title, all_repo_urls)
    print(f"   Found {len(configured_issues)} issues from configured repositories")

    if len(configured_issues) < len(all_issues):
        missing = len(all_issues) - len(configured_issues)
        print(f"\n   ⚠️  {missing} issues are from repositories NOT in your config!")
        print("   Add those repositories to the [repositories] section in config.ini")

    # Show which products would get which issues
    if configured_issues:
        print("\n9. Issues grouped by product:")
        from changelog_generator import ChangelogGenerator
        generator = ChangelogGenerator(repository_mapping)
        grouped = generator.group_issues_by_product(configured_issues)

        for product, issues in sorted(grouped.items()):
            print(f"   - {product}: {len(issues)} issues")

if __name__ == '__main__':
    main()
