"""GitHub Organization Metrics Collector."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from github import Github
from github.Organization import Organization
from github.Repository import Repository

logger = logging.getLogger(__name__)


@dataclass
class RepoMetrics:
    """Metrics for a single repository."""

    name: str
    full_name: str
    stars: int
    forks: int
    watchers: int
    open_issues: int
    open_pull_requests: int
    size_kb: int
    language: Optional[str]
    is_fork: bool
    is_archived: bool
    is_private: bool
    created_at: datetime
    updated_at: datetime
    pushed_at: Optional[datetime]


@dataclass
class OrgMetrics:
    """Aggregated metrics for an organization."""

    name: str
    total_repos: int
    public_repos: int
    private_repos: int
    total_members: int
    total_teams: int
    total_stars: int
    total_forks: int
    total_open_issues: int
    total_open_prs: int
    repos: list[RepoMetrics]


class GitHubCollector:
    """Collects metrics from a GitHub organization."""

    def __init__(self, token: str, org_name: str):
        """Initialize the collector.

        Args:
            token: GitHub personal access token
            org_name: Name of the GitHub organization
        """
        self.github = Github(token)
        self.org_name = org_name
        self._org: Optional[Organization] = None

    @property
    def org(self) -> Organization:
        """Get the organization object."""
        if self._org is None:
            self._org = self.github.get_organization(self.org_name)
        return self._org

    def _get_repo_metrics(self, repo: Repository) -> RepoMetrics:
        """Collect metrics for a single repository."""
        try:
            open_prs = repo.get_pulls(state="open").totalCount
        except Exception as e:
            logger.warning(f"Failed to get PRs for {repo.name}: {e}")
            open_prs = 0

        return RepoMetrics(
            name=repo.name,
            full_name=repo.full_name,
            stars=repo.stargazers_count,
            forks=repo.forks_count,
            watchers=repo.watchers_count,
            open_issues=repo.open_issues_count,
            open_pull_requests=open_prs,
            size_kb=repo.size,
            language=repo.language,
            is_fork=repo.fork,
            is_archived=repo.archived,
            is_private=repo.private,
            created_at=repo.created_at,
            updated_at=repo.updated_at,
            pushed_at=repo.pushed_at,
        )

    def collect(self) -> OrgMetrics:
        """Collect all metrics for the organization.

        Returns:
            OrgMetrics object containing all collected metrics
        """
        logger.info(f"Collecting metrics for organization: {self.org_name}")

        # Get organization-level metrics
        try:
            total_members = self.org.get_members().totalCount
        except Exception as e:
            logger.warning(f"Failed to get members count: {e}")
            total_members = 0

        try:
            total_teams = self.org.get_teams().totalCount
        except Exception as e:
            logger.warning(f"Failed to get teams count: {e}")
            total_teams = 0

        # Collect repository metrics
        repos_metrics: list[RepoMetrics] = []
        total_stars = 0
        total_forks = 0
        total_open_issues = 0
        total_open_prs = 0
        public_repos = 0
        private_repos = 0

        for repo in self.org.get_repos():
            try:
                metrics = self._get_repo_metrics(repo)
                repos_metrics.append(metrics)

                total_stars += metrics.stars
                total_forks += metrics.forks
                total_open_issues += metrics.open_issues
                total_open_prs += metrics.open_pull_requests

                if metrics.is_private:
                    private_repos += 1
                else:
                    public_repos += 1

            except Exception as e:
                logger.error(f"Failed to collect metrics for {repo.name}: {e}")

        org_metrics = OrgMetrics(
            name=self.org_name,
            total_repos=len(repos_metrics),
            public_repos=public_repos,
            private_repos=private_repos,
            total_members=total_members,
            total_teams=total_teams,
            total_stars=total_stars,
            total_forks=total_forks,
            total_open_issues=total_open_issues,
            total_open_prs=total_open_prs,
            repos=repos_metrics,
        )

        logger.info(
            f"Collected metrics: {org_metrics.total_repos} repos, "
            f"{org_metrics.total_stars} stars, {org_metrics.total_forks} forks"
        )

        return org_metrics
