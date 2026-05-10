"""Jira Cloud REST API client and endpoint wrappers.

The architectural pivot of this package is the dual-mode authentication —
see :mod:`jwe.api.auth` and :mod:`jwe.api.url_builder`. Higher-level modules
(:mod:`search`, :mod:`worklog`, :mod:`user`) compose these primitives via the
:class:`jwe.api.client.JiraCloudClient`.

External code should not reach for ``requests`` directly; it should always go
through ``JiraCloudClient`` so that auth headers and base URLs are handled
correctly for both Service Account and personal-token modes.
"""
