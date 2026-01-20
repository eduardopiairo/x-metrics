"""Prometheus metrics exporter for GitHub organization metrics."""

import logging
import threading
import time
from typing import Optional

from prometheus_client import Gauge, Info, CollectorRegistry, generate_latest

from .github_collector import GitHubCollector, OrgMetrics

logger = logging.getLogger(__name__)


class MetricsExporter:
    """Exports GitHub metrics to Prometheus format."""

    def __init__(self, collector: GitHubCollector, registry: Optional[CollectorRegistry] = None):
        """Initialize the exporter.

        Args:
            collector: GitHubCollector instance
            registry: Prometheus registry (uses default if not provided)
        """
        self.collector = collector
        self.registry = registry or CollectorRegistry()
        self._setup_metrics()
        self._last_metrics: Optional[OrgMetrics] = None
        self._lock = threading.Lock()

    def _setup_metrics(self):
        """Set up Prometheus metrics."""
        # Organization-level metrics
        self.org_info = Info(
            "github_org",
            "GitHub organization information",
            registry=self.registry,
        )

        self.org_repos_total = Gauge(
            "github_org_repos_total",
            "Total number of repositories",
            ["org"],
            registry=self.registry,
        )

        self.org_repos_public = Gauge(
            "github_org_repos_public",
            "Number of public repositories",
            ["org"],
            registry=self.registry,
        )

        self.org_repos_private = Gauge(
            "github_org_repos_private",
            "Number of private repositories",
            ["org"],
            registry=self.registry,
        )

        self.org_members_total = Gauge(
            "github_org_members_total",
            "Total number of organization members",
            ["org"],
            registry=self.registry,
        )

        self.org_teams_total = Gauge(
            "github_org_teams_total",
            "Total number of teams",
            ["org"],
            registry=self.registry,
        )

        self.org_stars_total = Gauge(
            "github_org_stars_total",
            "Total stars across all repositories",
            ["org"],
            registry=self.registry,
        )

        self.org_forks_total = Gauge(
            "github_org_forks_total",
            "Total forks across all repositories",
            ["org"],
            registry=self.registry,
        )

        self.org_open_issues_total = Gauge(
            "github_org_open_issues_total",
            "Total open issues across all repositories",
            ["org"],
            registry=self.registry,
        )

        self.org_open_prs_total = Gauge(
            "github_org_open_prs_total",
            "Total open pull requests across all repositories",
            ["org"],
            registry=self.registry,
        )

        # Repository-level metrics
        self.repo_stars = Gauge(
            "github_repo_stars",
            "Number of stars",
            ["org", "repo"],
            registry=self.registry,
        )

        self.repo_forks = Gauge(
            "github_repo_forks",
            "Number of forks",
            ["org", "repo"],
            registry=self.registry,
        )

        self.repo_watchers = Gauge(
            "github_repo_watchers",
            "Number of watchers",
            ["org", "repo"],
            registry=self.registry,
        )

        self.repo_open_issues = Gauge(
            "github_repo_open_issues",
            "Number of open issues",
            ["org", "repo"],
            registry=self.registry,
        )

        self.repo_open_prs = Gauge(
            "github_repo_open_prs",
            "Number of open pull requests",
            ["org", "repo"],
            registry=self.registry,
        )

        self.repo_size_kb = Gauge(
            "github_repo_size_kb",
            "Repository size in KB",
            ["org", "repo"],
            registry=self.registry,
        )

        self.repo_is_fork = Gauge(
            "github_repo_is_fork",
            "Whether the repository is a fork (1=yes, 0=no)",
            ["org", "repo"],
            registry=self.registry,
        )

        self.repo_is_archived = Gauge(
            "github_repo_is_archived",
            "Whether the repository is archived (1=yes, 0=no)",
            ["org", "repo"],
            registry=self.registry,
        )

        self.repo_is_private = Gauge(
            "github_repo_is_private",
            "Whether the repository is private (1=yes, 0=no)",
            ["org", "repo"],
            registry=self.registry,
        )

        # Collection metadata
        self.last_collection_timestamp = Gauge(
            "github_metrics_last_collection_timestamp",
            "Timestamp of last successful collection",
            ["org"],
            registry=self.registry,
        )

        self.collection_duration_seconds = Gauge(
            "github_metrics_collection_duration_seconds",
            "Duration of last collection in seconds",
            ["org"],
            registry=self.registry,
        )

    def update_metrics(self) -> None:
        """Collect and update all metrics."""
        start_time = time.time()

        try:
            metrics = self.collector.collect()

            with self._lock:
                self._last_metrics = metrics

                org = metrics.name

                # Update organization info
                self.org_info.info({"name": org})

                # Update organization-level metrics
                self.org_repos_total.labels(org=org).set(metrics.total_repos)
                self.org_repos_public.labels(org=org).set(metrics.public_repos)
                self.org_repos_private.labels(org=org).set(metrics.private_repos)
                self.org_members_total.labels(org=org).set(metrics.total_members)
                self.org_teams_total.labels(org=org).set(metrics.total_teams)
                self.org_stars_total.labels(org=org).set(metrics.total_stars)
                self.org_forks_total.labels(org=org).set(metrics.total_forks)
                self.org_open_issues_total.labels(org=org).set(metrics.total_open_issues)
                self.org_open_prs_total.labels(org=org).set(metrics.total_open_prs)

                # Update repository-level metrics
                for repo in metrics.repos:
                    self.repo_stars.labels(org=org, repo=repo.name).set(repo.stars)
                    self.repo_forks.labels(org=org, repo=repo.name).set(repo.forks)
                    self.repo_watchers.labels(org=org, repo=repo.name).set(repo.watchers)
                    self.repo_open_issues.labels(org=org, repo=repo.name).set(repo.open_issues)
                    self.repo_open_prs.labels(org=org, repo=repo.name).set(repo.open_pull_requests)
                    self.repo_size_kb.labels(org=org, repo=repo.name).set(repo.size_kb)
                    self.repo_is_fork.labels(org=org, repo=repo.name).set(1 if repo.is_fork else 0)
                    self.repo_is_archived.labels(org=org, repo=repo.name).set(
                        1 if repo.is_archived else 0
                    )
                    self.repo_is_private.labels(org=org, repo=repo.name).set(
                        1 if repo.is_private else 0
                    )

                # Update collection metadata
                self.last_collection_timestamp.labels(org=org).set(time.time())

            duration = time.time() - start_time
            self.collection_duration_seconds.labels(org=org).set(duration)
            logger.info(f"Metrics updated successfully in {duration:.2f}s")

        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")
            raise

    def get_metrics(self) -> bytes:
        """Generate Prometheus metrics output.

        Returns:
            Prometheus metrics in text format
        """
        return generate_latest(self.registry)


class MetricsCollectionLoop:
    """Background loop for periodic metrics collection."""

    def __init__(self, exporter: MetricsExporter, interval_seconds: int = 300):
        """Initialize the collection loop.

        Args:
            exporter: MetricsExporter instance
            interval_seconds: Collection interval in seconds
        """
        self.exporter = exporter
        self.interval = interval_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the collection loop in a background thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Collection loop already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"Started metrics collection loop (interval: {self.interval}s)")

    def stop(self) -> None:
        """Stop the collection loop."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
        logger.info("Stopped metrics collection loop")

    def _run(self) -> None:
        """Run the collection loop."""
        # Initial collection
        try:
            self.exporter.update_metrics()
        except Exception as e:
            logger.error(f"Initial metrics collection failed: {e}")

        while not self._stop_event.wait(self.interval):
            try:
                self.exporter.update_metrics()
            except Exception as e:
                logger.error(f"Metrics collection failed: {e}")
