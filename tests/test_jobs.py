import importlib.util
import sys
import types
from pathlib import Path


def _load_jobs_module(monkeypatch):
    choices = types.ModuleType('proxmox2netbox.choices')
    choices.SyncTypeChoices = types.SimpleNamespace(
        ALL='all', DEVICES='devices', VIRTUAL_MACHINES='virtual-machines'
    )
    service = types.ModuleType('proxmox2netbox.services.proxmox_sync')
    service.sync_devices = lambda: None
    service.sync_full_update = lambda: None
    service.sync_virtual_machines = lambda: None
    monkeypatch.setitem(sys.modules, 'proxmox2netbox.choices', choices)
    monkeypatch.setitem(sys.modules, 'proxmox2netbox.services.proxmox_sync', service)

    path = Path(__file__).parents[1] / 'proxmox2netbox' / 'jobs.py'
    spec = importlib.util.spec_from_file_location('_jobs_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _QuerySet:
    def __init__(self, records):
        self.records = records

    def filter(self, **criteria):
        def matches(record):
            for key, value in criteria.items():
                if key.endswith('__in'):
                    if record[key[:-4]] not in value:
                        return False
                elif key.endswith('__isnull'):
                    if (record[key[:-8]] is None) is not value:
                        return False
                elif record[key] != value:
                    return False
            return True

        return _QuerySet([record for record in self.records if matches(record)])

    def update(self, **values):
        for record in self.records:
            record.update(values)

    def delete(self):
        for record in self.records:
            record['deleted'] = True


def test_cancel_schedule_stops_running_recurrence_without_deleting_job(monkeypatch):
    jobs = _load_jobs_module(monkeypatch)
    records = [
        {'name': jobs.SCHEDULE_JOB_NAME, 'interval': 60, 'status': 'running'},
        {'name': jobs.SCHEDULE_JOB_NAME, 'interval': 60, 'status': 'scheduled'},
        {'name': 'Another Job', 'interval': 60, 'status': 'scheduled'},
    ]
    job_model = types.SimpleNamespace(objects=_QuerySet(records))

    jobs.cancel_scheduled_sync_jobs(job_model)

    assert records[0] == {
        'name': jobs.SCHEDULE_JOB_NAME,
        'interval': None,
        'status': 'running',
    }
    assert records[1]['deleted'] is True
    assert 'deleted' not in records[2]
