"""T077: GitHub webhook handler — create task files for actionable GitHub events."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def handle_github_event(event_type: str, payload: dict, task_dir: str) -> str | None:
    """Process a GitHub webhook event and create a task if actionable.
    Returns task_id if a task was created, None otherwise.
    """
    from backend.src.models.task import TaskCreate, TaskSource, TaskType, TaskPriority
    from backend.src.services.task_writer import write_task_file

    action = payload.get("action", "")
    repo = payload.get("repository", {}).get("full_name", "unknown")
    task_dir_path = Path(task_dir)

    if event_type == "pull_request" and action in ("opened", "review_requested"):
        pr = payload.get("pull_request", {})
        create_data = TaskCreate(
            type=TaskType.CODING_TASK,
            priority=TaskPriority.HIGH,
            source=TaskSource.GITHUB,
            instruction=f"Review pull request #{pr.get('number')}: {pr.get('title')}",
            context=(
                f"Repository: {repo}\n"
                f"Author: {pr.get('user', {}).get('login', 'unknown')}\n"
                f"Description: {pr.get('body', 'No description')}\n"
                f"Changed files: {pr.get('changed_files', 0)}\n"
                f"Additions: {pr.get('additions', 0)}, Deletions: {pr.get('deletions', 0)}"
            ),
            source_ref=pr.get("html_url"),
        )
        task_id, _ = write_task_file(create_data, task_dir_path)
        return task_id

    elif event_type == "pull_request_review" and action == "submitted":
        review = payload.get("review", {})
        pr = payload.get("pull_request", {})
        if review.get("state") == "changes_requested":
            create_data = TaskCreate(
                type=TaskType.CODING_TASK,
                priority=TaskPriority.HIGH,
                source=TaskSource.GITHUB,
                instruction=f"Address review feedback on PR #{pr.get('number')}: {pr.get('title')}",
                context=(
                    f"Repository: {repo}\n"
                    f"Reviewer: {review.get('user', {}).get('login', 'unknown')}\n"
                    f"Review body: {review.get('body', 'No body')}"
                ),
                source_ref=review.get("html_url"),
            )
            task_id, _ = write_task_file(create_data, task_dir_path)
            return task_id

    elif event_type == "issues" and action in ("opened", "assigned"):
        issue = payload.get("issue", {})
        labels = [l.get("name", "") for l in issue.get("labels", [])]
        create_data = TaskCreate(
            type=TaskType.CODING_TASK,
            priority=TaskPriority.MEDIUM,
            source=TaskSource.GITHUB,
            instruction=f"Address issue #{issue.get('number')}: {issue.get('title')}",
            context=(
                f"Repository: {repo}\n"
                f"Labels: {', '.join(labels)}\n"
                f"Body: {issue.get('body', 'No body')}"
            ),
            source_ref=issue.get("html_url"),
        )
        task_id, _ = write_task_file(create_data, task_dir_path)
        return task_id

    return None
