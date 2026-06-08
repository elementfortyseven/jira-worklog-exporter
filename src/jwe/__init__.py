"""Jira Cloud Worklog Exporter.

Exports worklogs of selected users from a Jira Cloud site to CSV.

The package is structured into:
- ``jwe.api``: HTTP client and endpoint wrappers for the Jira Cloud REST API.
- ``jwe.adf``: Atlassian Document Format (ADF) -> plain text conversion.
- ``jwe.exporter``: Domain orchestration that ties it all together.
- ``jwe.csv_writer``: Streaming CSV output.
- ``jwe.config``: Typed configuration dataclass.
- ``jwe.cli`` / ``jwe.gui``: User-facing entry points.
"""

__version__ = "1.1.0"
