"""Products repository — thin wrapper around :class:`db.lookup.LookupRepo`."""

from __future__ import annotations

from db.lookup import products_repo as _repo

# Re-export the public API as module-level functions so existing
# ``import db.products as products_repo`` call-sites keep working.
create = _repo.create
list_products = _repo.list
rename = _repo.rename
archive = _repo.archive
get = _repo.get

# Backwards compat alias — now public via ``get``.
_get = get
