# Release Notes

## v1.2.12

### Reliability — bounded sync jobs

Proxmox API requests now use a 30-second timeout so an unreachable endpoint
cannot occupy a NetBox RQ worker indefinitely. Disabling a recurring schedule
also clears recurrence from a running job while cancelling work that has not
started.

### Security — sync actions and credentials

Manual synchronization uses CSRF-protected POST requests. Endpoint edit forms
no longer render stored passwords or token secrets, and journal API operations
are limited to valid Proxmox2NetBox sync processes.

### CI/CD

GitHub workflows now use the Node.js 24-based releases of `actions/checkout`
and `actions/setup-python`.

---

## v1.2.10

### Added — Per-endpoint sync controls

Each Proxmox endpoint can now control which data domains are synced:

- nodes
- QEMU virtual machines
- LXC containers
- VM interfaces
- VM IP addresses
- QEMU guest-agent IP fallback
- virtual disks
- stale plugin-managed interface/IP/disk pruning

Endpoints can also be disabled without deleting their configuration.

### Fixed — NetBox permission alignment

Plugin views now use NetBox object permissions consistently. Normal users can
open plugin pages, run manual sync actions, view sync history, and manage node
type mappings with standard NetBox permissions.

### Fixed — NetBox 4.5 runtime issues

The UI and sync flow were tested against NetBox 4.5.8, including plugin
templates, API routes, endpoint sync controls, and direct full-update service
runs.

---

## v1.2.9

### Fixed — Manual VM interface IPs are no longer deleted during sync

Automatic IP cleanup is now limited to IP addresses previously managed by `proxmox2netbox`.
If Proxmox provides no authoritative IP data for an interface, existing NetBox IP assignments are preserved.

### Added — Regression coverage for interface IP sync

Tests now verify that:

- existing IPs are preserved when Proxmox returns no IP data
- only plugin-managed stale IPs are deleted when authoritative IPs exist
- matching IPs retain assignment and update VRF/tag state correctly

---

## v1.2.6

### Fixed — Stale IPs not cleaned up on interfaces with no configured IPs

`_sync_iface_ips` was only called when the wanted IP set was non-empty. Interfaces that had IPs removed from Proxmox config never had their old IPs deleted from NetBox.

**Fix:** `_sync_iface_ips` is now always called — even with an empty wanted set it removes stale IPs.

### Fixed — `NameError: manufacturer` when endpoint has a custom device type

`manufacturer` was only defined inside `if device_type is None:` but referenced in the return dict outside it. Sync crashed when `netbox_device_type` was set on the endpoint.

---

## v1.2.5

### Fixed — IPs assigned to wrong interface (all IPs went to `eth0`)

`_extract_interface_ips` returned a flat list of all IPs for a VM; all were assigned to the first interface.

**Fix:** Returns `{net_idx: [ips]}` per interface. QEMU guest agent IPs matched by MAC address via `_try_agent_ips_by_mac`.

---

## v1.2.4

### Added — Per-node Device Type Mapping UI

New `ProxmoxNodeTypeMapping` model with full CRUD UI (`Plugins → Proxmox2NetBox → Configuration → Node Type Mappings`). Map individual node names to specific NetBox DeviceTypes.

### Fixed — Migration drift (0016), NoReverseMatch, TypeError: api_url, TemplateDoesNotExist

Several follow-up fixes for the new model and form.

### Performance — Gunicorn cold-start

`preload_app = True` added to `gunicorn.py`.

---

## v1.2.3

### Added — Per-endpoint Node Device Type

`netbox_device_type` FK on `ProxmoxEndpoint`. Synced nodes get the selected DeviceType (e.g. Dell PowerEdge R740) instead of always using the generic *Proxmox Node*.

Endpoint detail page, list table, and API serializer updated to expose the new field.

---

## v1.2.2

### Fixed — `IPNetwork.split()` crash and additional IP sync bugs

---

## v1.2.1

### Fixed — NetBox 4.x cluster scope and VMInterface MAC address

---

## v1.2.0

### Added — Site/VRF mapping, per-interface IP sync, guest-agent fallback

- `netbox_site` and `netbox_vrf` FK fields on `ProxmoxEndpoint`.
- IPs from Proxmox VM config synced to correct `VMInterface` per interface index.
- QEMU guest agent queried as IP fallback.

---

## v1.1.4

### Initial stable release

Plugin correctly registered in NetBox. Basic sync of Proxmox nodes, QEMU VMs, and LXC containers.
