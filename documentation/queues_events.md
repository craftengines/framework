# Events & Queues

Craft features a synchronous Event Dispatcher to decouple logic within request lifecycles, and an asynchronous Queue System to execute heavy tasks in background processes.

---

## Events & Listeners

Events serve as placeholders indicating something has happened, and Listeners intercept those occurrences.

### 1. Defining the Event
Events are typically simple datastructure wrappers:

```python
class PostPublished:
    def __init__(self, post_id: str):
        self.post_id = post_id
```

### 2. Defining the Listener
Listeners define a `handle(event)` method:

```python
from app.Models.Post import Post
from craft.facades import Log

class SendPostNotifications:
    async def handle(self, event: PostPublished):
        post = await Post.find(event.post_id)
        Log.info(f"Sending notifications for post: {post.title}")
```

### 3. Registering & Dispatching
Map your events to listeners inside your `EventServiceProvider` boot method:

```python
from craft.facades import Event

# Mapping
Event.listen(PostPublished, [SendPostNotifications])

# Dispatching anywhere in your app code
Event.dispatch(PostPublished(post_id="post-uuid"))
```

---

## Asynchronous Queues

Queue processing shifts time-consuming tasks (like email delivery or file parsing) to a background worker.

### Defining Jobs
Jobs inherit from the base class `craft.queue.Job`. They must define a `handle()` method.

> [!CAUTION]
> **Strict JSON Serialization Requirement**:
> To prevent security vulnerabilities, Craft processes job payloads using JSON serialization rather than Python's `pickle` library.
> Do **NOT** pass complex object instances (such as database Model instances or connection objects) to Job constructor parameters.
> Instead, pass scalar attributes (such as database primary keys, strings, or numbers) and query the corresponding model instance from the database inside the job's `handle()` method.

```python
from craft.queue import Job
from app.Models.User import User
from craft.facades import Log

class SendWelcomeEmail(Job):
    def __init__(self, user_id: str):
        # Pass simple scalar types to the constructor
        self.user_id = user_id

    async def handle(self):
        # Reload database models inside the handler
        user = await User.find(self.user_id)
        if user:
            Log.info(f"Sending welcome email to: {user.email}")
```

### Dispatching Jobs
Push jobs to the queue using the `Queue` facade:

```python
from craft.facades import Queue

# Push the job into background processing
Queue.push(SendWelcomeEmail(user_id="user-uuid"))
```

### Running the Worker
Background tasks are processed using the background queue worker command:

```bash
python dev.py queue:work
```
This starts a persistent loop polling the database/queue for jobs and executing them.
