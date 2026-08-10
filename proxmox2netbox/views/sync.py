from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from django_htmx.middleware import HtmxDetails

from proxmox2netbox.services.proxmox_sync import (
    sync_devices as sync_devices_service,
    sync_full_update as sync_full_update_service,
    sync_virtual_machines as sync_virtual_machines_service,
)


class HtmxHttpRequest(HttpRequest):
    htmx: HtmxDetails


def _run_sync(request: HtmxHttpRequest, template_name: str, partial_template_name: str, sync_callable) -> HttpResponse:
    result = {}
    try:
        result = sync_callable() or {}
    except Exception as exc:  # noqa: BLE001
        result = {"errors": [str(exc)]}

    is_htmx = getattr(request, 'htmx', None)
    if not is_htmx:
        if result.get("errors"):
            messages.warning(request, f"Sync completed with {len(result['errors'])} error(s).")
        else:
            messages.success(request, "Sync completed successfully.")
        return render(request, template_name, {"result": result})
    return render(request, partial_template_name, {"result": result})


@permission_required("proxmox2netbox.change_proxmoxendpoint", raise_exception=True)
@require_POST
def sync_devices(request: HtmxHttpRequest) -> HttpResponse:
    return _run_sync(
        request=request,
        template_name="proxmox2netbox/sync_devices.html",
        partial_template_name="proxmox2netbox/partials/sync_devices.html",
        sync_callable=sync_devices_service,
    )


@permission_required("proxmox2netbox.change_proxmoxendpoint", raise_exception=True)
@require_POST
def sync_virtual_machines(request: HtmxHttpRequest) -> HttpResponse:
    return _run_sync(
        request=request,
        template_name="proxmox2netbox/sync_virtual_machines.html",
        partial_template_name="proxmox2netbox/partials/sync_virtual_machines.html",
        sync_callable=sync_virtual_machines_service,
    )


@permission_required("proxmox2netbox.change_proxmoxendpoint", raise_exception=True)
@require_POST
def sync_full_update(request: HtmxHttpRequest) -> HttpResponse:
    return _run_sync(
        request=request,
        template_name="proxmox2netbox/sync_full_update.html",
        partial_template_name="proxmox2netbox/partials/sync_full_update.html",
        sync_callable=sync_full_update_service,
    )


SCHEDULE_JOB_NAME = 'Proxmox2NetBox Sync'

INTERVAL_CHOICES = [
    (0, 'Disabled'),
    (60, 'Every 1 hour'),
    (180, 'Every 3 hours'),
    (360, 'Every 6 hours'),
    (720, 'Every 12 hours'),
    (1440, 'Every 24 hours'),
]


def _get_scheduled_job():
    from core.models import Job
    return Job.objects.filter(
        name=SCHEDULE_JOB_NAME,
        interval__isnull=False,
        status__in=('pending', 'scheduled', 'running'),
    ).order_by('-created').first()


@permission_required("proxmox2netbox.view_proxmoxendpoint", raise_exception=True)
@require_GET
def get_sync_schedule(request: HtmxHttpRequest) -> HttpResponse:
    job = _get_scheduled_job()
    return render(request, 'proxmox2netbox/partials/sync_schedule.html', {
        'scheduled_job': job,
        'interval_choices': INTERVAL_CHOICES,
        'current_interval': job.interval if job else 0,
    })


@permission_required("proxmox2netbox.change_proxmoxendpoint", raise_exception=True)
@require_POST
def set_sync_schedule(request: HtmxHttpRequest) -> HttpResponse:
    from core.models import Job
    from proxmox2netbox.jobs import Proxmox2NetBoxSyncJob
    from proxmox2netbox.choices import SyncTypeChoices

    try:
        interval = int(request.POST.get('interval', 0))
    except (TypeError, ValueError):
        return HttpResponseBadRequest('Invalid sync interval.')

    allowed_intervals = {value for value, _label in INTERVAL_CHOICES}
    if interval not in allowed_intervals:
        return HttpResponseBadRequest('Invalid sync interval.')

    # Cancel existing scheduled jobs
    Job.objects.filter(
        name=SCHEDULE_JOB_NAME,
        interval__isnull=False,
        status__in=('pending', 'scheduled', 'running'),
    ).delete()

    if interval > 0:
        Proxmox2NetBoxSyncJob.enqueue(
            sync_type=SyncTypeChoices.ALL,
            interval=interval,
        )
        messages.success(request, f"Scheduled sync every {interval} minutes.")
    else:
        messages.success(request, "Scheduled sync disabled.")

    job = _get_scheduled_job()
    return render(request, 'proxmox2netbox/partials/sync_schedule.html', {
        'scheduled_job': job,
        'interval_choices': INTERVAL_CHOICES,
        'current_interval': job.interval if job else 0,
    })
