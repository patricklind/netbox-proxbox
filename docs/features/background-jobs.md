# Background Jobs

Proxmox2NetBox integrates with NetBox's built-in job system (RQ workers).

## Job class

`Proxmox2NetBoxSyncJob` in `proxmox2netbox/jobs.py` is a `JobRunner` subclass registered as a NetBox system job.

## Triggering sync

**From UI:**

- `Plugins → Proxmox2NetBox → Full Update` — runs full sync for all enabled endpoints

**From NetBox shell:**

```python
from proxmox2netbox.jobs import Proxmox2NetBoxSyncJob
from proxmox2netbox.choices import SyncTypeChoices

Proxmox2NetBoxSyncJob.enqueue(sync_type=SyncTypeChoices.ALL)
Proxmox2NetBoxSyncJob.enqueue(sync_type=SyncTypeChoices.DEVICES)
Proxmox2NetBoxSyncJob.enqueue(sync_type=SyncTypeChoices.VIRTUAL_MACHINES)
```

## Job behavior

- The job class is an orchestrator only — all sync mapping and upsert logic lives in `services/proxmox_sync.py`.
- Jobs run in NetBox RQ workers (`netbox-rq` service).
- Proxmox API requests have a 30-second timeout so an unreachable endpoint
  cannot occupy an RQ worker indefinitely.
- Job results are visible in `Admin → Jobs` in the NetBox UI.
- If an RQ worker is restarted, make sure it picks up the latest installed package version.
