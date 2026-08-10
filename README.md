# Proxmox2NetBox

NetBox plugin for synchronizing Proxmox inventory data into NetBox (NetBox v4).

> [!WARNING]
> We are aware that there are issues in the codebase.
> This is a hobby project maintained in spare time.
> Fixes and improvements are implemented when time allows.
> Do not deploy in production without proper validation.

## Compatibility

- NetBox: `>=4.2.0, <5.0.0`
- Python: `>=3.11`
- Plugin package version in this repository: `1.2.12`

## What Works (Current Runtime)

Out-of-the-box sync requires only a configured **Proxmox Endpoint** in NetBox.

Implemented sync flows:

- Proxmox nodes → NetBox `dcim.Device`
- Proxmox QEMU/LXC VMs → NetBox `virtualization.VirtualMachine`
- VM interfaces from Proxmox config → NetBox `virtualization.VMInterface`, with per-interface IP assignment
- QEMU guest-agent IPs as fallback when static config lacks IPs (MAC-based interface matching)
- Endpoint-level **Site** and **VRF** mapping — devices and IPs are placed in the correct NetBox Site/VRF
- Endpoint-level **Node Device Type** — select a real NetBox DeviceType (e.g. Dell PowerEdge R740) for synced nodes; falls back to generic *Proxmox Node* type
- **Per-node Device Type Mapping** — override device type per individual node name via *Node Type Mappings* UI (`Plugins → Proxmox2NetBox → Configuration → Node Type Mappings`)
- **Per-endpoint sync controls** — enable/disable each endpoint and choose nodes, QEMU VMs, LXC containers, VM interfaces, VM IPs, guest-agent IP fallback, virtual disks, and stale-object pruning
- Endpoint metadata refresh (`mode`, `version`, `repoid`, cluster name)
- Sync process tracking in `SyncProcess`
- Stale IP cleanup — plugin-managed IPs removed from Proxmox config are removed from NetBox interfaces when endpoint pruning is enabled

## Runtime Architecture (Source of Truth)

Core sync logic is consolidated in:

- `proxmox2netbox/services/proxmox_sync.py`

Backward-compatible import shim (kept intentionally):

- `proxmox2netbox/proxmox_sync.py`

Primary runtime entrypoints:

- UI endpoints: `proxmox2netbox/views/sync.py`
- Connection/status badge: `proxmox2netbox/views/keepalive_status.py`
- Proxmox card data: `proxmox2netbox/views/cards.py`
- Job wrapper: `proxmox2netbox/jobs.py` (`Proxmox2NetBoxSyncJob`)

## Installation (NetBox v4)

### 1. Install plugin package

Inside NetBox environment:

```bash
pip install proxmox2netbox
```

If you run `netbox-docker`, also pin the package in your Docker requirements file so it survives rebuilds/redeploys:

```text
# local_requirements.txt
proxmox2netbox==1.2.12
```

### 2. Enable plugin

In NetBox `configuration.py`:

```python
PLUGINS = ["proxmox2netbox"]
```

### 3. Run migrations/static

```bash
python manage.py migrate
python manage.py collectstatic --no-input
```

## Configure and Run Sync

### Configure Proxmox Endpoint

In NetBox UI:

- `Plugins -> Proxmox2NetBox -> Endpoints -> Proxmox Endpoints`
- Create at least one endpoint with:
  - `username`
  - either `password` **or** (`token_name` + `token_value`)
  - host via `domain` and/or `ip_address`
  - optional NetBox Site/VRF/Node Device Type mapping
  - optional sync controls for what this endpoint may create, update, and prune

Per-endpoint sync controls default to the previous behavior: endpoint enabled,
nodes enabled, QEMU and LXC VM sync enabled, VM interfaces/IPs/disks enabled,
guest-agent IP fallback enabled, and stale plugin-managed interfaces/IPs/disks
pruned when Proxmox no longer reports them.

### NetBox Permissions

For regular NetBox users, use object permissions:

- `view` on `proxmox2netbox.ProxmoxEndpoint` to open the plugin home page and
  endpoint status cards
- `change` on `proxmox2netbox.ProxmoxEndpoint` to run manual sync actions or
  change the sync schedule
- `view` on `proxmox2netbox.SyncProcess` to view sync history
- `view/add/change/delete` on `proxmox2netbox.ProxmoxNodeTypeMapping` to manage
  per-node device type mappings

### Run sync from UI

- `Plugins -> Proxmox2NetBox -> Full Update`
- Available actions:
  - `Sync Nodes`
  - `Sync Virtual Machines`
  - `Full Update Sync`

### Run sync as NetBox Job (wrapper)

`jobs.py` provides a queue-compatible wrapper around the existing service layer.

Example from NetBox shell:

```python
from proxmox2netbox.jobs import Proxmox2NetBoxSyncJob
from proxmox2netbox.choices import SyncTypeChoices

# Full sync
Proxmox2NetBoxSyncJob.enqueue(sync_type=SyncTypeChoices.ALL)

# Devices only
Proxmox2NetBoxSyncJob.enqueue(sync_type=SyncTypeChoices.DEVICES)

# Virtual machines only
Proxmox2NetBoxSyncJob.enqueue(sync_type=SyncTypeChoices.VIRTUAL_MACHINES)
```

Behavior note:

- Job class is an orchestrator only.
- Sync mapping, payloads, and upsert logic remain in `services/proxmox_sync.py`.

## Development & Validation

### Static checks

```bash
ruff check proxmox2netbox --select F401,F403,F811,F821,F841,E712
python -m compileall -q proxmox2netbox
```

### Django checks (inside NetBox runtime)

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
```

### Tests

The repository includes pytest coverage for the sync services, parsers, API
views, and UI views.

```bash
pytest
```

## Publish to PyPI

### Prerequisites

- You must have access to the [`proxmox2netbox`](https://pypi.org/project/proxmox2netbox/) project on PyPI.
- If the name is unavailable for your account, change `project.name` in `pyproject.toml` to a unique name before publishing.
- Configure a matching Trusted Publisher in PyPI for this GitHub repository/workflow:
- Owner: `patricklind`
- Repository: `Proxmox2Netbox`
- Workflow file: `.github/workflows/publish-python-package.yml`
- Environment name: `pypi`

### Local preflight

```bash
python -m build
twine check dist/*
```

### Publish via GitHub Actions

- Bump `version` in `pyproject.toml` and plugin config version in source.
- Create and push a tag:

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

- `release.yml` creates the GitHub Release from the tag after lint/tests pass.
- `publish-python-package.yml` publishes to PyPI using GitHub OIDC Trusted Publisher.
- If no publish run appears after the release is created, run **Publish Python Package** manually from Actions for the same tag. GitHub releases created by Actions with `GITHUB_TOKEN` do not always emit a follow-up event that starts another workflow.
- After publish:

```bash
pip install proxmox2netbox
```

## Repository Layout (Relevant Runtime Files)

```text
proxmox2netbox/
  __init__.py
  jobs.py
  choices.py
  filtersets.py
  navigation.py
  models/
    __init__.py              # ProxmoxEndpoint, ProxmoxNodeTypeMapping, SyncProcess
  services/
    proxmox_sync.py          # Core sync logic (nodes, VMs, interfaces, IPs)
  proxmox_sync.py            # Backward-compat import shim
  views/
    __init__.py
    sync.py
    keepalive_status.py
    cards.py
    node_type_mapping.py     # CRUD views for ProxmoxNodeTypeMapping
  forms/
    __init__.py
    proxmox.py               # Endpoint + NodeTypeMapping forms
  tables/
    __init__.py
  api/
    serializers.py           # Endpoint, node type mapping, and sync process serializers
    views.py                 # NetBox REST API viewsets
  migrations/
    0001_initial.py … 0020_endpoint_sync_controls.py
  templates/
    proxmox2netbox/
      home.html
      proxmoxendpoint.html
      proxmoxnodetypemapping.html
      syncprocess.html
      inc/
  urls.py
```

## Scope

This repository ships a NetBox plugin runtime only.  
Legacy FastAPI/backend-service components are removed from runtime, docs, and packaging scope.

## Wiki

- GitHub Wiki URL: `https://github.com/patricklind/Proxmox2Netbox/wiki`
- Wiki source files in this repository: `wiki/`
