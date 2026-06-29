from core.services.payload_normalizer import normalize_pull_request_event


GITLAB_PAYLOAD = {
    "object_kind": "merge_request",
    "project": {"id": 105, "path_with_namespace": "team/backend"},
    "object_attributes": {"iid": 12, "title": "feat: API", "source_branch": "feature/x"},
}

GITHUB_PAYLOAD = {
    "action": "opened",
    "pull_request": {
        "number": 42,
        "title": "feat: API",
        "head": {"ref": "feature/x"},
    },
    "repository": {"full_name": "owner/repo"},
}


def test_normalize_gitlab_merge_request():
    event = normalize_pull_request_event(GITLAB_PAYLOAD)
    assert event is not None
    assert event.provider == "gitlab"
    assert event.ref.project_ref == "105"
    assert event.ref.number == 12


def test_normalize_github_pull_request():
    event = normalize_pull_request_event(GITHUB_PAYLOAD)
    assert event is not None
    assert event.provider == "github"
    assert event.ref.project_ref == "owner/repo"
    assert event.ref.number == 42


def test_ignore_github_closed_action():
    payload = {**GITHUB_PAYLOAD, "action": "closed"}
    assert normalize_pull_request_event(payload) is None


def test_ignore_unrelated_payload():
    assert normalize_pull_request_event({"object_kind": "push"}) is None
