import os

from fastapi import FastAPI, Response
from prometheus_client import CollectorRegistry

from .github_collector import GitHubCollector
from .metrics_exporter import MetricsExporter, MetricsCollectionLoop

app = FastAPI()

# Global references
_collection_loop: MetricsCollectionLoop | None = None
_exporter: MetricsExporter | None = None


@app.on_event("startup")
def startup():
    global _collection_loop, _exporter

    github_token = os.environ.get("GITHUB_TOKEN")
    github_org = os.environ.get("GITHUB_ORG")
    collection_interval = int(os.environ.get("COLLECTION_INTERVAL", "300"))

    if not github_token:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    if not github_org:
        raise ValueError("GITHUB_ORG environment variable is required")

    registry = CollectorRegistry()
    collector = GitHubCollector(token=github_token, org_name=github_org)
    _exporter = MetricsExporter(collector=collector, registry=registry)
    _collection_loop = MetricsCollectionLoop(exporter=_exporter, interval_seconds=collection_interval)
    _collection_loop.start()


@app.on_event("shutdown")
def shutdown():
    if _collection_loop:
        _collection_loop.stop()


@app.get("/")
def index():
    return {"message": "GitHub Metrics Collector"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    if _exporter is None:
        return Response(content="Exporter not initialized", status_code=503)
    return Response(content=_exporter.get_metrics(), media_type="text/plain; charset=utf-8")
