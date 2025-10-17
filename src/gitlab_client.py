"""GitLab API client for fetching milestone and issue data."""

import gitlab
from typing import List, Dict, Optional, Union


class GitLabClient:
    """Client for interacting with GitLab API."""

    def __init__(self, url: str, token: str, group_id: str):
        """
        Initialize GitLab client for group milestones.

        Args:
            url: GitLab instance URL
            token: Private access token
            group_id: Group ID or path
        """
        self.gl = gitlab.Gitlab(url, private_token=token)
        self.group_id = group_id
        self.group = self.gl.groups.get(group_id)

    def get_milestone_by_name(self, milestone_name: str) -> Optional[object]:
        """
        Get milestone by name.

        Args:
            milestone_name: Name of the milestone

        Returns:
            Milestone object or None if not found
        """
        milestones = self.group.milestones.list(search=milestone_name, get_all=True)
        for milestone in milestones:
            if milestone.title == milestone_name:
                return milestone
        return None

    def get_milestone_by_id(self, milestone_id: int) -> object:
        """
        Get milestone by ID.

        Args:
            milestone_id: Milestone ID

        Returns:
            Milestone object
        """
        return self.group.milestones.get(milestone_id)

    def get_projects_in_group(self) -> List[object]:
        """
        Get all projects in the group.

        Returns:
            List of project objects
        """
        projects = self.group.projects.list(get_all=True, include_subgroups=True)
        return projects

    def get_project_by_url(self, project_url: str) -> Optional[object]:
        """
        Get project object by its GitLab URL.

        Args:
            project_url: Full project URL

        Returns:
            Project object or None if not found
        """
        # Extract project path from URL
        try:
            # Remove trailing slash if present
            project_url = project_url.rstrip('/')

            # Extract path after the domain
            parts = project_url.split('/')
            if len(parts) >= 2:
                # Get the last two parts (namespace/project)
                project_path = '/'.join(parts[-2:])

                try:
                    return self.gl.projects.get(project_path)
                except gitlab.exceptions.GitlabGetError:
                    return None
        except Exception as e:
            print(f"Error parsing project URL {project_url}: {e}")
            return None

    def get_closed_issues(self, milestone_title: str, project_urls: List[str]) -> List[Dict]:
        """
        Get all closed issues for a group milestone from specified repositories.

        Args:
            milestone_title: Milestone title (not ID - GitLab API requires the title for group milestones)
            project_urls: List of project URLs to filter issues from (for filtering results)

        Returns:
            List of issue dictionaries with relevant data
        """
        issue_data = []

        # Normalize project URLs for filtering
        normalized_urls = set(url.rstrip('/') for url in project_urls)

        # Fetch issues directly from the group milestone
        # This is the correct way to get issues from a group milestone
        # IMPORTANT: GitLab API requires milestone TITLE (not ID) for group milestones
        try:
            # Use the group's issues endpoint with milestone filter
            issues = self.group.issues.list(
                milestone=milestone_title,
                state='closed',
                get_all=True
            )

            print(f"Found {len(issues)} closed issues in group milestone")

            # Filter issues by project URL if project_urls is provided
            for issue in issues:
                # Get the project for this issue
                try:
                    project = self.gl.projects.get(issue.project_id)
                    project_url = project.web_url.rstrip('/')

                    # Only include if the project is in our configured list
                    if project_url in normalized_urls:
                        issue_data.append({
                            'iid': issue.iid,
                            'title': issue.title,
                            'labels': issue.labels,
                            'web_url': issue.web_url,
                            'project_name': project.name,
                            'project_url': project.web_url,
                            'time_stats': {
                                'time_estimate': issue.time_stats.get('time_estimate', 0),
                                'total_time_spent': issue.time_stats.get('total_time_spent', 0)
                            }
                        })
                except Exception as e:
                    print(f"Warning: Could not get project info for issue #{issue.iid}: {e}")
                    continue

        except Exception as e:
            print(f"Error fetching issues from group milestone: {e}")

        return issue_data

    def get_closed_merge_requests(self, milestone_id: int) -> List[Dict]:
        """
        Get all merged merge requests for a milestone.

        Args:
            milestone_id: Milestone ID

        Returns:
            List of merge request dictionaries
        """
        merge_requests = self.project.mergerequests.list(
            milestone=str(milestone_id),
            state='merged',
            get_all=True
        )

        mr_data = []
        for mr in merge_requests:
            mr_data.append({
                'iid': mr.iid,
                'title': mr.title,
                'labels': mr.labels,
                'web_url': mr.web_url
            })

        return mr_data

    def test_connection(self) -> bool:
        """
        Test connection to GitLab API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.gl.auth()
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
