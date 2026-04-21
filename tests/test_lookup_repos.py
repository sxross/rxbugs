"""Tests for the four parallel lookup-table repositories:

* ``db.products``
* ``db.areas``
* ``db.severities``
* ``db.platforms``

They share the same shape (create / list / rename / archive / _get),
so the tests are parameterised.
"""

from __future__ import annotations

import pytest

from db import areas as areas_repo
from db import bugs as bugs_repo
from db import platforms as platforms_repo
from db import products as products_repo
from db import severities as severities_repo


# (module, bug_field_name, list_fn_name)
_REPOS = [
    (products_repo, "product", "list_products"),
    (areas_repo, "area", "list_areas"),
    (severities_repo, "severity", "list_severities"),
    (platforms_repo, "platform", "list_platforms"),
]


@pytest.mark.parametrize("repo, field, list_fn", _REPOS)
def test_create_returns_entry_with_zero_bug_count(engine, repo, field, list_fn):
    entry = repo.create(engine, name="Alpha", description="desc")
    assert entry["name"] == "Alpha"
    assert entry["description"] == "desc"
    assert entry["archived"] is False
    assert entry["bug_count"] == 0


@pytest.mark.parametrize("repo, field, list_fn", _REPOS)
def test_list_includes_bug_count(engine, repo, field, list_fn):
    repo.create(engine, name="Alpha")
    bugs_repo.create(
        engine, product="Alpha" if field == "product" else "P",
        title="b", actor="u", actor_type="human",
        **{field: "Alpha"} if field != "product" else {},
    )
    entries = getattr(repo, list_fn)(engine)
    alpha = next(e for e in entries if e["name"] == "Alpha")
    assert alpha["bug_count"] == 1


@pytest.mark.parametrize("repo, field, list_fn", _REPOS)
def test_list_excludes_archived_by_default(engine, repo, field, list_fn):
    repo.create(engine, name="A")
    repo.create(engine, name="Z")
    repo.archive(engine, "Z")
    names = [e["name"] for e in getattr(repo, list_fn)(engine)]
    assert "A" in names
    assert "Z" not in names

    names_all = [e["name"] for e in getattr(repo, list_fn)(engine, include_archived=True)]
    assert "Z" in names_all


@pytest.mark.parametrize("repo, field, list_fn", _REPOS)
def test_rename_also_updates_bugs(engine, repo, field, list_fn):
    repo.create(engine, name="Old")
    bugs_repo.create(
        engine, product="Old" if field == "product" else "P",
        title="t", actor="u", actor_type="human",
        **({field: "Old"} if field != "product" else {}),
    )
    renamed = repo.rename(engine, "Old", "New")
    assert renamed is not None
    assert renamed["name"] == "New"
    # The bug should now reference the new name.
    bug = bugs_repo.get(engine, "BUG-0001")
    assert bug[field] == "New"


@pytest.mark.parametrize("repo, field, list_fn", _REPOS)
def test_archive_flips_archived_flag(engine, repo, field, list_fn):
    repo.create(engine, name="Foo")
    archived = repo.archive(engine, "Foo")
    assert archived["archived"] is True


@pytest.mark.parametrize("repo, field, list_fn", _REPOS)
def test_get_missing_returns_none(engine, repo, field, list_fn):
    assert repo._get(engine, "does-not-exist") is None


@pytest.mark.parametrize("repo, field, list_fn", _REPOS)
def test_create_is_idempotent(engine, repo, field, list_fn):
    first = repo.create(engine, name="Dup", description="first")
    second = repo.create(engine, name="Dup", description="ignored")
    # INSERT OR IGNORE keeps the first description.
    assert second["description"] == first["description"]
