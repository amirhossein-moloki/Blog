# Celery & Async Task Documentation

The Blog Platform uses Celery with Redis for asynchronous task execution and scheduled jobs.

---

## Queue Architecture
Tasks are distributed across three specialized queues to ensure optimal resource allocation:

| Queue | Priority | Purpose |
| :--- | :--- | :--- |
| `high_priority` | High | User-facing tasks like password resets and auth emails. |
| `default` | Medium | Standard background operations like post publishing and notifications. |
| `low_priority` | Low | Resource-intensive background tasks. |

---

## Task Registry

### 1. `posts.tasks.publish_scheduled_posts_task`
- **Purpose:** Scans the database for posts marked as 'scheduled' whose `publish_at` time has passed.
- **Trigger:** Automated (Celery Beat).
- **Service Called:** `posts.services.publish_scheduled_posts()`.

### 2. `interactions.tasks.notify_author_on_new_comment`
- **Purpose:** Sends a notification (email/dashboard) to a post author when a new comment is approved.
- **Trigger:** Manual (called in `CommentViewSet.perform_create`).

---

## Scheduled Jobs (Celery Beat)

The following jobs are configured in `settings.py`:

| Job Name | Task | Schedule |
| :--- | :--- | :--- |
| `publish-scheduled-posts` | `posts.tasks.publish_scheduled_posts_task` | Every 1 Minute |

---

## Error Handling & Retries
- **Automatic Retries:** Network-dependent tasks (like email sending) are configured with exponential backoff.
- **Result Backend:** Task results are stored in Redis (DB 1) for 24 hours.
- **Monitoring:** Flower can be used to monitor task success/failure rates (if configured in infrastructure).

---

## Local Development
To run a worker locally:
```bash
celery -A blog worker --loglevel=info
```

To run the scheduler:
```bash
celery -A blog beat --loglevel=info
```
