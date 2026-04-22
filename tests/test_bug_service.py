"""Tests for BugService."""

import pytest

import db.annotations as annotations_repo
import db.bugs as bugs_repo
import db.relations as relations_repo
from services import BugService


def test_close_bug_with_annotation_transactional(engine):
    """close_bug_with_annotation should execute in single transaction."""
    service = BugService(engine)
    
    # Create a bug
    bug = bugs_repo.create(
        engine,
        product="RxTrack",
        title="Test bug",
        actor="human",
        actor_type="human",
    )
    bug_id = bug["id"]
    
    # Close with annotation
    result = service.close_bug_with_annotation(
        bug_id=bug_id,
        resolution="fixed",
        annotation_body="Fixed in commit abc123",
        actor="human",
        actor_type="human",
    )
    
    # Verify bug was closed
    assert result["bug"]["status"] == "closed"
    assert result["bug"]["resolution"] == "fixed"
    
    # Verify annotation was created
    annotations = annotations_repo.list_for_bug(engine, bug_id)
    assert len(annotations) == 1
    assert annotations[0]["body"] == "Fixed in commit abc123"
    assert annotations[0]["author"] == "human"


def test_close_bug_without_annotation(engine):
    """close_bug_with_annotation should work without annotation body."""
    service = BugService(engine)
    
    bug = bugs_repo.create(
        engine,
        product="RxTrack",
        title="Test bug",
        actor="human",
        actor_type="human",
    )
    
    result = service.close_bug_with_annotation(
        bug_id=bug["id"],
        resolution="wont_fix",
        annotation_body=None,
        actor="human",
        actor_type="human",
    )
    
    assert result["bug"]["status"] == "closed"
    assert result["bug"]["resolution"] == "wont_fix"
    
    # No annotation should be created
    annotations = annotations_repo.list_for_bug(engine, bug["id"])
    assert len(annotations) == 0


def test_close_bug_duplicate_warning_no_relations(engine):
    """Closing as duplicate without relations should generate warning."""
    service = BugService(engine)
    
    bug = bugs_repo.create(
        engine,
        product="RxTrack",
        title="Duplicate bug",
        actor="human",
        actor_type="human",
    )
    
    result = service.close_bug_with_annotation(
        bug_id=bug["id"],
        resolution="duplicate",
        annotation_body=None,
        actor="human",
        actor_type="human",
    )
    
    assert len(result["warnings"]) == 1
    assert "canonical bug" in result["warnings"][0]


def test_close_bug_duplicate_no_warning_with_relations(engine):
    """Closing as duplicate with relations should not generate warning."""
    service = BugService(engine)
    
    # Create two bugs
    bug1 = bugs_repo.create(
        engine,
        product="RxTrack",
        title="Original bug",
        actor="human",
        actor_type="human",
    )
    bug2 = bugs_repo.create(
        engine,
        product="RxTrack",
        title="Duplicate bug",
        actor="human",
        actor_type="human",
    )
    
    # Link bug2 to bug1 (canonical)
    relations_repo.link(engine, bug2["id"], bug1["id"], actor="human", actor_type="human")
    
    result = service.close_bug_with_annotation(
        bug_id=bug2["id"],
        resolution="duplicate",
        annotation_body=None,
        actor="human",
        actor_type="human",
    )
    
    assert "warnings" not in result


def test_close_bug_fixed_warning_no_annotation(engine):
    """Closing as fixed without annotation should generate warning."""
    service = BugService(engine)
    
    bug = bugs_repo.create(
        engine,
        product="RxTrack",
        title="Bug to fix",
        actor="human",
        actor_type="human",
    )
    
    result = service.close_bug_with_annotation(
        bug_id=bug["id"],
        resolution="fixed",
        annotation_body=None,
        actor="human",
        actor_type="human",
    )
    
    assert len(result["warnings"]) == 1
    assert "without an annotation" in result["warnings"][0]


def test_close_bug_fixed_no_warning_with_annotation(engine):
    """Closing as fixed with annotation should not generate warning."""
    service = BugService(engine)
    
    bug = bugs_repo.create(
        engine,
        product="RxTrack",
        title="Bug to fix",
        actor="human",
        actor_type="human",
    )
    
    result = service.close_bug_with_annotation(
        bug_id=bug["id"],
        resolution="fixed",
        annotation_body="Fixed in commit xyz789",
        actor="human",
        actor_type="human",
    )
    
    assert "warnings" not in result


def test_close_bug_fixed_no_warning_with_existing_annotations(engine):
    """Closing as fixed with existing annotations should not generate warning."""
    service = BugService(engine)
    
    bug = bugs_repo.create(
        engine,
        product="RxTrack",
        title="Bug to fix",
        actor="human",
        actor_type="human",
    )
    
    # Add an existing annotation
    annotations_repo.create(
        engine,
        bug_id=bug["id"],
        author="human",
        author_type="human",
        body="Working on this",
    )
    
    result = service.close_bug_with_annotation(
        bug_id=bug["id"],
        resolution="fixed",
        annotation_body=None,
        actor="human",
        actor_type="human",
    )
    
    # No warning because there's already an annotation
    assert "warnings" not in result


def test_close_already_closed_bug_raises(engine):
    """Closing an already-closed bug should raise ValueError."""
    service = BugService(engine)
    
    bug = bugs_repo.create(
        engine,
        product="RxTrack",
        title="Bug",
        actor="human",
        actor_type="human",
    )
    
    # Close it once
    bugs_repo.close(engine, bug["id"], resolution="fixed", actor="human", actor_type="human")
    
    # Try to close again
    with pytest.raises(ValueError, match="already closed"):
        service.close_bug_with_annotation(
            bug_id=bug["id"],
            resolution="duplicate",
            annotation_body=None,
            actor="human",
            actor_type="human",
        )
