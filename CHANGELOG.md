# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

## [1.2.12] - 2026-08-10

### Security

- Manual synchronization actions now require CSRF-protected `POST` requests.
- Endpoint edit forms no longer render stored passwords or API token secrets.
- Journal entry API access is restricted to valid Proxmox2NetBox sync processes.

### Fixed

- Proxmox API requests now time out after 30 seconds instead of occupying a
  NetBox RQ worker indefinitely when an endpoint is unresponsive.
- Recurring sync schedules can be disabled without deleting an executing job.
- Invalid recurring schedule intervals are rejected before queue state changes.

### CI/CD

- Updated `actions/checkout` and `actions/setup-python` to Node.js 24-based
  releases.

### Tests

- Added regression coverage for recurring-job cancellation and Proxmox request
  timeout propagation.

## [1.2.10] - 2026-04-20

### Added

- **Endpoint sync controls** — added per-endpoint sync configuration for controlling which Proxmox data domains are synced.

### Fixed

- **NetBox permission alignment** — plugin views now use NetBox permissions consistently.
- **Model and UI compatibility fixes** — resolved runtime issues in the Proxmox2NetBox UI and sync flow discovered during NetBox 4.5 testing.

---

## [1.2.9] - 2026-03-16

### Fixed

- **VM interface IP sync no longer deletes manual IP assignments** — interface IP cleanup is now limited to IP addresses previously managed by `proxmox2netbox`. If Proxmox provides no authoritative IPs for an interface, existing NetBox IP assignments are preserved.
- **Managed IP ownership is now tagged consistently** — IPs created or updated by sync are tagged with the plugin managed tag, allowing safe future cleanup of only plugin-managed addresses.

### Tests

- Added regression coverage for interface IP sync to verify:
- existing IPs are preserved when Proxmox returns no IP data
- only plugin-managed stale IPs are deleted when authoritative IPs exist
- matching IPs keep assignment and update VRF/tag state correctly

---

## [1.2.8] - 2026-03-01

### Fixed

- **Silent exception swallowing removed** — bare `except Exception: pass` blocks narrowed to specific types (`ValueError`, `LookupError`) with `logger.debug` logging so failures appear in logs.
- **False-positive bandit B105 suppressed** — validation error messages containing "Token" no longer generate spurious security warnings.

---

## [1.2.7] - 2026-03-01

### Security

- **API: credentials no longer returned in GET responses** — `password` and `token_value` are now `write_only` in `ProxmoxEndpointSerializer`. Accepted in POST/PATCH but never included in responses.
- **`ContributingView`: removed SSRF risk** — previously made two unauthenticated HTTP calls to the GitHub API on every page load. Now reads `CONTRIBUTING.md` from the local filesystem. `github.py` and the dead-code `release.py` (which referenced NetBox 2.8/2.9/2.10) have been deleted.
- **`verify_ssl` default changed to `True`** — new `ProxmoxEndpoint` records default to verifying SSL certificates (migration `0017`). Existing records are unaffected.

### Fixed

- **`ProxmoxEndpoint.__str__` with no IP address** — previously rendered `"Endpoint (None)"`. Now uses `domain`, then bare IP, then `'no address'` as fallback.
- **`CommonProperties.url` protocol** — used `http://` when `verify_ssl=False`. The `url` property now always uses `https://`; `verify_ssl` controls certificate verification only.
- **`JournalEntryViewSet`**: `object_id` query param now validated as an integer before ORM filter; returns empty queryset for non-integer input.

### Changed

- **Parse utilities extracted to `_parse.py`** — all side-effect-free Proxmox config parsing functions moved to `proxmox2netbox/services/_parse.py` (no Django/NetBox dependencies). Call sites in `proxmox_sync.py` are unchanged.
- **Seven regex patterns pre-compiled at module level** in `_parse.py` instead of being recompiled on every loop iteration.
- **`sync_run=None` parameter removed** from `sync_devices()`, `sync_virtual_machines()`, `sync_full_update()` — the parameter was never used.
- **`requires-python >= 3.11`** in `pyproject.toml`; removed obsolete 3.8/3.9/3.10 classifiers; streamlined `dev` extras.

### CI/CD

- Updated GitHub Actions to `checkout@v4`, `setup-python@v5`, Python 3.11 + 3.12.
- Replaced `flake8` with `ruff`, added `bandit` security scan, `build + twine check`, and a `pytest` test job.

### Tests

- **45 unit tests** added (`tests/test_parse.py`) covering all parse utility functions — no Django/NetBox setup required.

---

## [1.2.6] - 2026-02-28

### Fixed — **Stale IPs not cleaned up on interfaces with no configured IPs**

`_sync_iface_ips` was only called when `ip_strs` was non-empty (`if ip_strs:` guard).
Interfaces that had IPs in a previous sync but now have no IPs configured in Proxmox never had their old IPs removed.

**Fix:** `_sync_iface_ips` is now always called — even with an empty wanted set it deletes stale IPs.

### Fixed — **`NameError: manufacturer` when endpoint has a custom device type set**

`manufacturer` was only defined inside the `if device_type is None:` block but referenced in the return dict outside it.
Sync would crash with a `NameError` whenever an endpoint had `netbox_device_type` configured.

**Fix:** `manufacturer` is now initialised to `None` before the block.

### Files changed

| File | Change |
|---|---|
| `proxmox2netbox/services/proxmox_sync.py` | Always call `_sync_iface_ips`; initialise `manufacturer = None` before conditional block |

---

## [1.2.5] - 2026-02-28

### Fixed — **IPs assigned to wrong interface (all IPs went to `eth0`)**

`_extract_interface_ips` returned a flat list of *all* IPs for a VM.
`_upsert_vm_interfaces` assigned that entire list to the first interface it processed.

**Fix:**

- `_extract_interface_ips` now returns `{net_idx: [ips]}` — one list per interface index.
- `_try_agent_ips` replaced by `_try_agent_ips_by_mac` which returns `{MAC_UPPER: [ips]}`.
  QEMU guest-agent IPs are matched to the correct interface via MAC address.
- `_upsert_vm_interfaces` uses per-interface IPs from config, falling back to MAC-based agent IPs.

### Files changed

| File | Change |
|---|---|
| `proxmox2netbox/services/proxmox_sync.py` | `_extract_interface_ips` → dict; `_try_agent_ips_by_mac`; per-interface IP assignment in `_upsert_vm_interfaces` |

---

## [1.2.4] - 2026-02-28

### Added — **Per-node Device Type Mapping UI**

New model `ProxmoxNodeTypeMapping` — map a specific Proxmox node name (e.g. `pve01`) to a specific NetBox `DeviceType`.

- Full CRUD UI under *Plugins → Proxmox2NetBox → Configuration → Node Type Mappings*.
- Sync respects the mapping: nodes with an explicit mapping get that device type; others use the endpoint default (or generic fallback).
- Prevents sync from overwriting manually set device types for unmapped nodes.

### Added — Migration `0015_proxmox_node_type_mapping.py`

Creates the `proxmox2netbox_proxmoxnodetypemapping` table.

### Fixed — Migration drift `0016_proxmoxnodetypemapping_fix.py`

Migration 0015 was missing the `tags` field (`taggit.managers.TaggableManager`) and used the wrong encoder for `custom_field_data` (must be `utilities.json.CustomFieldJSONEncoder`). Migration 0016 corrects both.

### Fixed — `NoReverseMatch: 'proxmoxendpoint-list'` on node-type-mapping create page

`DynamicModelChoiceField` attempted to auto-resolve the API URL for `ProxmoxEndpoint` (non-standard path `endpoints/proxmox/`).
**Fix:** switched to `forms.ModelChoiceField` with `select_related('ip_address')`.

### Fixed — `TypeError: api_url unexpected keyword argument`

NetBox 4.5's `DynamicModelChoiceField` does not accept an `api_url` parameter.
**Fix:** switched to `ModelChoiceField`.

### Fixed — `TemplateDoesNotExist: proxmoxnodetypemapping.html`

Created detail template for the new model.

### Performance — Gunicorn cold-start (~12 s on first request)

Added `preload_app = True` to `/opt/netbox/gunicorn.py`. Gunicorn now loads all Python modules at server startup instead of on the first request per worker.

### Files changed

| File | Change |
|---|---|
| `proxmox2netbox/models/__init__.py` | New `ProxmoxNodeTypeMapping` model |
| `proxmox2netbox/migrations/0015_proxmox_node_type_mapping.py` | Create mapping table |
| `proxmox2netbox/migrations/0016_proxmoxnodetypemapping_fix.py` | Fix encoder + tags |
| `proxmox2netbox/forms/proxmox.py` | `ProxmoxNodeTypeMappingForm` using `ModelChoiceField` |
| `proxmox2netbox/filtersets.py` | `ProxmoxNodeTypeMappingFilterSet` |
| `proxmox2netbox/tables/__init__.py` | `ProxmoxNodeTypeMappingTable` |
| `proxmox2netbox/views/node_type_mapping.py` | CRUD views |
| `proxmox2netbox/views/__init__.py` | Export new views |
| `proxmox2netbox/urls.py` | URL patterns for node type mapping |
| `proxmox2netbox/navigation.py` | Navigation item under "Configuration" |
| `proxmox2netbox/templates/proxmox2netbox/proxmoxnodetypemapping.html` | New detail template |
| `proxmox2netbox/services/proxmox_sync.py` | Node type mapping lookup in sync |
| `/opt/netbox/gunicorn.py` | `preload_app = True` |

---

## [1.2.3] - 2026-02-28

### Added — **Per-endpoint Node Device Type**

New `netbox_device_type` ForeignKey field on `ProxmoxEndpoint` (→ `dcim.DeviceType`).

Select a real NetBox DeviceType (e.g. *Dell PowerEdge R740*) to assign to all Proxmox nodes synced from this endpoint.
If not set, the generic *Proxmox Node* device type is used as a fallback.

### Added — Migration `0014_proxmoxendpoint_device_type.py`

FK column added with `SET_NULL` on delete.

### Added — Endpoint detail template improvements

Endpoint detail page now shows rows for: Domain, Version, Site (with link), VRF (with link), Node Device Type (with link or fallback text).

### Added — Endpoint list table columns

`netbox_site` and `netbox_device_type` columns added to the endpoint list table.

### Added — API serializer fields

`netbox_site`, `netbox_vrf`, and `netbox_device_type` are now exposed on `ProxmoxEndpointSerializer`.

### Changed — Sync logic

- `_ensure_base_objects(mode, site=None, device_type=None)` — accepts an optional `device_type`.
- `_upsert_all_for_session` reads `endpoint.netbox_device_type` and passes it through.

### Files changed

| File | Change |
|---|---|
| `proxmox2netbox/models/__init__.py` | `netbox_device_type` FK on `ProxmoxEndpoint` |
| `proxmox2netbox/migrations/0014_proxmoxendpoint_device_type.py` | FK migration |
| `proxmox2netbox/forms/proxmox.py` | `netbox_device_type` form field |
| `proxmox2netbox/tables/__init__.py` | Site + device type columns |
| `proxmox2netbox/templates/proxmox2netbox/proxmoxendpoint.html` | Site/VRF/Device Type rows |
| `proxmox2netbox/api/serializers.py` | Expose new fields |
| `proxmox2netbox/services/proxmox_sync.py` | Pass device type through sync |

---

## [1.2.2] - 2026-02-28

### Fixed — **`IPNetwork.split()` crash + additional bugs**

- `IPNetwork.split()` called incorrectly — replaced with correct netaddr API usage.
- Additional minor bug fixes in IP sync path.

### Files changed

| File | Change |
|---|---|
| `proxmox2netbox/services/proxmox_sync.py` | Fix `IPNetwork.split()` usage; IP sync bug fixes |

---

## [1.2.1] - 2026-02-28

### Fixed — **NetBox 4.x compatibility**

- Cluster `scope` set correctly — NetBox 4.x uses a generic `scope` field instead of `site`.
- `VMInterface` primary MAC address handled correctly for NetBox 4.5's `MACAddress` model.

### Files changed

| File | Change |
|---|---|
| `proxmox2netbox/services/proxmox_sync.py` | Cluster scope fix; VMInterface MAC address fix |

---

## [1.2.0] - 2026-02-28

### Added — **Site/VRF mapping, IP sync, guest-agent IP fallback**

- `ProxmoxEndpoint` can now be linked to a NetBox **Site** and **VRF**.
  Synced devices are placed in the configured site; IPs are assigned to the configured VRF.
- IPs are synced from Proxmox VM config (`net0`, `net1`, …) to NetBox `VMInterface`.
- QEMU guest agent is used as fallback for IP addresses when the VM config contains no static IPs.
- Migrations `0012_proxmoxendpoint_site` and `0013_proxmoxendpoint_site_vrf` add the FK fields.

### Files changed

| File | Change |
|---|---|
| `proxmox2netbox/models/__init__.py` | `netbox_site` and `netbox_vrf` FK fields |
| `proxmox2netbox/migrations/0012_*.py` | Site FK migration |
| `proxmox2netbox/migrations/0013_*.py` | VRF FK migration |
| `proxmox2netbox/forms/proxmox.py` | Site/VRF form fields |
| `proxmox2netbox/services/proxmox_sync.py` | IP sync; guest agent fallback |

---

## [1.1.4] - 2026-02-26

### Added — **First stable release on this system**

- Plugin correctly registered in NetBox (`PluginConfig`, migrations, navigation).
- Basic sync of Proxmox nodes, QEMU VMs, and LXC containers to NetBox.
- Migrations corrected and tested.
