"""Changelog generator that processes issues and formats output."""

import os
from collections import defaultdict
from datetime import datetime
from typing import List, Dict

from src import config


class ChangelogGenerator:
    """Generates formatted changelogs from GitLab issue data."""

    def __init__(self, repos_to_products: Dict[str, str]):
        """
        Initialize changelog generator.
        """
        # Create reverse mapping for repository to product
        self.repos_to_products = repos_to_products

    def group_issues_by_product(self, issues: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group issues by product based on repository URLs.

        Args:
            issues: List of issue dictionaries

        Returns:
            Dictionary with product names as keys and issue lists as values
        """
        grouped = defaultdict(list)

        for issue in issues:
            project_url = issue['project_url']
            product = self.repos_to_products.get(project_url)
            if not product:
                # If no repository match found, add to Uncategorized
                grouped['Uncategorized'].append(issue)
                continue
            grouped[product].append(issue)
        return dict(grouped)

    def format_issue_line(self, issue: Dict) -> str:
        """
        Format a single issue line for the changelog.

        Args:
            issue: Issue dictionary

        Returns:
            Formatted string with title, repository, issue number, and labels
        """
        # Extract only non-alias labels (not starting with @)
        labels = [l for l in issue['labels'] if not l.startswith('@')]

        # Get project name from issue data
        project_name = issue.get('project_name', 'unknown')

        # Format: * Title (repository#123) (label1, label2)
        issue_ref = f"{project_name}#{issue['iid']}"

        if labels:
            labels_str = ', '.join(labels)
            return f"* {issue['title']} ({issue_ref}) ({labels_str})"
        else:
            return f"* {issue['title']} ({issue_ref})"

    def generate_changelog(
        self,
        milestone_name: str,
        milestone_dates: tuple,
        issues: List[Dict],
        merge_requests: List[Dict] = None
    ) -> str:
        """
        Generate complete changelog text.

        Args:
            milestone_name: Name of the milestone
            milestone_dates: Tuple of (start_date, due_date)
            issues: List of issue dictionaries
            merge_requests: Optional list of merge request dictionaries

        Returns:
            Formatted changelog as string
        """
        start_date, due_date = milestone_dates

        # Format dates
        start_str = start_date.strftime('%Y-%m-%d') if start_date else 'N/A'
        due_str = due_date.strftime('%Y-%m-%d') if due_date else 'N/A'

        # Build changelog header
        changelog = f"**Changelog - {milestone_name}** ({start_str} → {due_str})\n\n"

        # Group issues by product
        grouped_issues = self.group_issues_by_product(issues)

        # Sort products (Uncategorized at the end)
        sorted_products = sorted(
            grouped_issues.keys(),
            key=lambda x: (x == 'Uncategorized', x)
        )

        # Format each product section
        for product in sorted_products:
            product_issues = grouped_issues[product]
            changelog += f"**{product}** ({len(product_issues)} issues)\n"

            # Sort issues alphabetically by title
            sorted_issues = sorted(product_issues, key=lambda x: x['title'].lower())

            for issue in sorted_issues:
                changelog += self.format_issue_line(issue) + "\n"

            changelog += "\n"

        # Add footer with statistics
        total_issues = len(issues)
        total_time_estimate = sum(
            issue['time_stats']['time_estimate'] for issue in issues
        )

        # Convert seconds to hours and days
        # GitLab uses 8 hours as 1 working day by default
        est_hours = total_time_estimate / 3600 if total_time_estimate else 0
        est_days = est_hours / 8 if est_hours > 0 else 0

        changelog += "---\n"
        changelog += f"Total: {total_issues} issues closed"

        if est_hours > 0:
            # Show both hours and days
            changelog += f" | Estimated: {est_hours:.1f}h ({est_days:.1f}d)"

        changelog += "\n"

        return changelog

    def generate_markdown_file(
        self,
        milestone_name: str,
        milestone_dates: tuple,
        issues: List[Dict],
        output_file: str,
        merge_requests: List[Dict] = None
    ) -> None:
        """
        Generate changelog and save to markdown file.

        Args:
            milestone_name: Name of the milestone
            milestone_dates: Tuple of (start_date, due_date)
            issues: List of issue dictionaries
            output_file: Path to output markdown file
            merge_requests: Optional list of merge request dictionaries
        """
        changelog = self.generate_changelog(
            milestone_name,
            milestone_dates,
            issues,
            merge_requests
        )

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(changelog)

    def append_to_year_changelog(
        self,
        milestone_name: str,
        milestone_dates: tuple,
        issues: List[Dict],
        archive_dir: str = 'changelog_archive',
        merge_requests: List[Dict] = None
    ) -> None:
        """
        Append or update changelog entry in year-based file (e.g., 2025.md).
        If milestone already exists, replace it; otherwise add at top.

        Args:
            milestone_name: Name of the milestone
            milestone_dates: Tuple of (start_date, due_date)
            issues: List of issue dictionaries
            archive_dir: Directory to store year-based changelogs (default: 'changelog_archive')
            merge_requests: Optional list of merge request dictionaries
        """
        import re

        # Extract year from milestone dates (use due_date or start_date)
        start_date, due_date = milestone_dates
        milestone_year = None

        if due_date:
            milestone_year = due_date.year
        elif start_date:
            milestone_year = start_date.year
        else:
            # Try to extract year from milestone name (e.g., "09/10/2025")
            year_match = re.search(r'(\d{4})', milestone_name)
            if year_match:
                milestone_year = int(year_match.group(1))
            else:
                milestone_year = datetime.now().year

        # Create archive directory if it doesn't exist
        os.makedirs(archive_dir, exist_ok=True)

        # Year file path
        year_file = os.path.join(archive_dir, f"{milestone_year}.md")

        # Generate new changelog entry
        new_entry = self.generate_changelog(
            milestone_name,
            milestone_dates,
            issues,
            merge_requests
        )

        # Add separator and timestamp
        current_time = datetime.now()
        new_entry += f"\n---\n*Generated on {current_time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n"

        # Read existing year file if it exists
        existing_content = ""
        if os.path.exists(year_file):
            with open(year_file, 'r', encoding='utf-8') as f:
                existing_content = f.read()

        # Check if this milestone already exists in the file
        milestone_pattern = re.escape(f"**Changelog - {milestone_name}**")
        milestone_exists = re.search(milestone_pattern, existing_content)

        if milestone_exists:
            # Replace existing milestone entry
            # Find the section for this milestone (from header to next header or separator)
            # Pattern: from "**Changelog - {name}**" to next "**Changelog -" or end of file
            pattern = (
                r'\*\*Changelog - ' + re.escape(milestone_name) + r'\*\*.*?'
                r'(?=\n\*\*Changelog - |\Z)'
            )
            existing_content = re.sub(
                pattern,
                new_entry.rstrip() + '\n\n',
                existing_content,
                flags=re.DOTALL
            )

            # Write updated content
            with open(year_file, 'w', encoding='utf-8') as f:
                f.write(existing_content)

            print(f"Updated existing milestone '{milestone_name}' in {year_file}")
        else:
            # Add new entry at the top
            with open(year_file, 'w', encoding='utf-8') as f:
                f.write(new_entry)
                if existing_content:
                    f.write(existing_content)

            print(f"Added new milestone '{milestone_name}' to {year_file}")

    def append_to_changelog(
        self,
        milestone_name: str,
        milestone_dates: tuple,
        issues: List[Dict],
        changelog_file: str = 'CHANGELOG.md',
        archive_dir: str = 'changelog_archive',
        merge_requests: List[Dict] = None
    ) -> None:
        """
        Append new changelog entry to the top of CHANGELOG.md and archive entries by year.
        (Legacy method - kept for backward compatibility)

        Args:
            milestone_name: Name of the milestone
            milestone_dates: Tuple of (start_date, due_date)
            issues: List of issue dictionaries
            changelog_file: Path to main CHANGELOG.md file (default: 'CHANGELOG.md')
            archive_dir: Directory to store archived changelogs by year (default: 'changelog_archive')
            merge_requests: Optional list of merge request dictionaries
        """
        # Generate new changelog entry
        new_entry = self.generate_changelog(
            milestone_name,
            milestone_dates,
            issues,
            merge_requests
        )

        # Add separator and timestamp
        current_time = datetime.now()
        current_year = current_time.year
        new_entry += f"\n---\n*Generated on {current_time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n"

        # Read existing changelog if it exists
        existing_content = ""
        if os.path.exists(changelog_file):
            with open(changelog_file, 'r', encoding='utf-8') as f:
                existing_content = f.read()

        # Archive old entries that belong to previous years
        if archive_dir and existing_content:
            # Create archive directory if it doesn't exist
            os.makedirs(archive_dir, exist_ok=True)

            # Parse the existing changelog to find entries from previous years
            # Look for year patterns in the content
            lines = existing_content.split('\n')
            current_year_content = []
            archive_entries_by_year = {}
            current_entry_year = None
            current_entry_lines = []

            for line in lines:
                # Look for date patterns like "2024-10-01" or "Generated on 2024-"
                if '202' in line or '201' in line:  # Basic year detection
                    # Try to extract year from the line
                    import re
                    year_match = re.search(r'(20\d{2})', line)
                    if year_match:
                        detected_year = int(year_match.group(1))
                        if current_entry_year != detected_year:
                            # Save previous entry if exists
                            if current_entry_year and current_entry_lines:
                                if current_entry_year == current_year:
                                    current_year_content.extend(current_entry_lines)
                                else:
                                    if current_entry_year not in archive_entries_by_year:
                                        archive_entries_by_year[current_entry_year] = []
                                    archive_entries_by_year[current_entry_year].extend(current_entry_lines)
                            current_entry_year = detected_year
                            current_entry_lines = [line]
                        else:
                            current_entry_lines.append(line)
                    else:
                        current_entry_lines.append(line)
                else:
                    current_entry_lines.append(line)

            # Save the last entry
            if current_entry_year and current_entry_lines:
                if current_entry_year == current_year:
                    current_year_content.extend(current_entry_lines)
                else:
                    if current_entry_year not in archive_entries_by_year:
                        archive_entries_by_year[current_entry_year] = []
                    archive_entries_by_year[current_entry_year].extend(current_entry_lines)

            # Write archived entries to their respective year files (prepend to top)
            for year, year_lines in archive_entries_by_year.items():
                year_file = os.path.join(archive_dir, f"{year}.md")
                year_content = '\n'.join(year_lines).strip()

                # Read existing year file if it exists
                existing_year_content = ""
                if os.path.exists(year_file):
                    with open(year_file, 'r', encoding='utf-8') as f:
                        existing_year_content = f.read()

                # Write to year file (new content at top)
                with open(year_file, 'w', encoding='utf-8') as f:
                    f.write(year_content)
                    if existing_year_content and not existing_year_content in year_content:
                        f.write("\n\n" + existing_year_content)

            # Keep only current year entries in the existing content
            existing_content = '\n'.join(current_year_content).strip()

        # Write new entry at the top
        with open(changelog_file, 'w', encoding='utf-8') as f:
            f.write(new_entry)
            if existing_content:
                f.write("\n" + existing_content)
