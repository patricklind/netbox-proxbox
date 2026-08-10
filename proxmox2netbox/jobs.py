"""NetBox job wrappers for Proxmox2NetBox synchronization."""

from netbox.jobs import JobFailed, JobRunner

from proxmox2netbox.choices import SyncTypeChoices
from proxmox2netbox.services.proxmox_sync import (
    sync_devices,
    sync_full_update,
    sync_virtual_machines,
)

SCHEDULE_JOB_NAME = 'Proxmox2NetBox Sync'


class Proxmox2NetBoxSyncJob(JobRunner):
    """Run the existing Proxmox -> NetBox sync flow inside NetBox job queue."""

    class Meta:
        name = "Proxmox2NetBox Sync"
        description = "Execute Proxmox synchronization using the plugin service layer"

    def run(self, sync_type: str = SyncTypeChoices.ALL):
        if sync_type == SyncTypeChoices.DEVICES:
            result = sync_devices()
        elif sync_type == SyncTypeChoices.VIRTUAL_MACHINES:
            result = sync_virtual_machines()
        elif sync_type == SyncTypeChoices.ALL:
            result = sync_full_update()
        else:
            raise JobFailed(f"Unsupported sync_type: {sync_type}")

        if result and result.get('errors'):
            raise JobFailed('; '.join(result['errors']))
        return result


def enqueue_sync_job(sync_type: str = SyncTypeChoices.ALL, interval=None):
    """Enqueue the Proxmox2NetBox sync job. Set interval (minutes) for recurring."""
    kwargs = {'sync_type': sync_type}
    if interval:
        kwargs['interval'] = interval
    return Proxmox2NetBoxSyncJob.enqueue(**kwargs)


def cancel_scheduled_sync_jobs(job_model=None):
    """Stop recurring sync jobs without deleting an executing job record."""
    if job_model is None:
        from core.models import Job

        job_model = Job

    jobs = job_model.objects.filter(
        name=SCHEDULE_JOB_NAME,
        interval__isnull=False,
    )
    jobs.filter(status='running').update(interval=None)
    jobs.filter(status__in=('pending', 'scheduled')).delete()
