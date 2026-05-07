"""Severities repository — thin wrapper around :class:`db.lookup.LookupRepo`."""

from __future__ import annotations

from db.lookup import severities_repo as _repo

create = _repo.create
list_severities = _repo.list
rename = _repo.rename
archive = _repo.archive
get = _repo.get

_get = get
