"""Regression tests for VM interface IP synchronization behavior."""
import importlib.util
import os
import sys
import types


def _stub(name: str, **attrs):
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    sys.modules[name] = mod
    return mod


_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
_PARSE_PATH = os.path.join(_ROOT, "proxmox2netbox", "services", "_parse.py")
_SYNC_PATH = os.path.join(_ROOT, "proxmox2netbox", "services", "proxmox_sync.py")


def _load_sync_module():
    _stub("dcim.models", Device=object, DeviceRole=object, DeviceType=object, MACAddress=object, Manufacturer=object, Site=object)
    _stub("ipam.models", IPAddress=object)
    _stub("extras.models.tags", Tag=object, TaggedItem=object)
    _stub("virtualization.models", Cluster=object, ClusterType=object, VirtualDisk=object, VMInterface=object, VirtualMachine=object)
    _stub("proxmox2netbox")
    _stub("proxmox2netbox.services")
    _stub(
        "proxmox2netbox.choices",
        ProxmoxModeChoices=types.SimpleNamespace(
            PROXMOX_MODE_CLUSTER="cluster",
            PROXMOX_MODE_STANDALONE="standalone",
            PROXMOX_MODE_UNDEFINED="undefined",
        ),
        SyncTypeChoices=types.SimpleNamespace(
            ALL="all",
            DEVICES="devices",
            VIRTUAL_MACHINES="virtual-machines",
        ),
    )
    _stub("proxmox2netbox.models", ProxmoxEndpoint=object, ProxmoxNodeTypeMapping=object)

    parse_spec = importlib.util.spec_from_file_location("proxmox2netbox.services._parse", _PARSE_PATH)
    parse_mod = importlib.util.module_from_spec(parse_spec)
    sys.modules["proxmox2netbox.services._parse"] = parse_mod
    parse_spec.loader.exec_module(parse_mod)

    sync_spec = importlib.util.spec_from_file_location("proxmox2netbox.services.proxmox_sync", _SYNC_PATH)
    sync_mod = importlib.util.module_from_spec(sync_spec)
    sys.modules["proxmox2netbox.services.proxmox_sync"] = sync_mod
    sync_spec.loader.exec_module(sync_mod)
    return sync_mod


_sync_mod = _load_sync_module()


class _FakeIP:
    def __init__(self, address, pk, vrf_id=None, assigned_object_id=10, assigned_object_type_id=None):
        self.address = address
        self.pk = pk
        self.vrf_id = vrf_id
        self.vrf = None
        self.assigned_object_id = assigned_object_id
        self.assigned_object_type_id = assigned_object_type_id
        self.deleted = False
        self.saved_update_fields = []

    def save(self, update_fields=None):
        self.saved_update_fields.append(update_fields or [])
        if self.vrf is not None:
            self.vrf_id = self.vrf.pk

    def delete(self):
        self.deleted = True


class _FakeIPManager:
    def __init__(self, existing):
        self._existing = list(existing)
        self.created = []

    def filter(self, **kwargs):
        results = list(self._existing)
        if "address" in kwargs:
            results = [ip for ip in results if ip.address == kwargs["address"]]
        if kwargs.get("vrf__isnull") is True:
            results = [ip for ip in results if ip.vrf_id is None]
        if "vrf" in kwargs:
            vrf = kwargs["vrf"]
            results = [ip for ip in results if ip.vrf_id == getattr(vrf, "pk", None)]
        if "assigned_object_id" in kwargs:
            results = [ip for ip in results if ip.assigned_object_id == kwargs["assigned_object_id"]]
        return results

    def create(self, **kwargs):
        new_ip = _FakeIP(
            kwargs["address"],
            pk=100 + len(self.created),
            vrf_id=getattr(kwargs.get("vrf"), "pk", None),
            assigned_object_id=kwargs.get("assigned_object_id"),
            assigned_object_type_id=getattr(kwargs.get("assigned_object_type"), "pk", None),
        )
        self.created.append(new_ip)
        self._existing.append(new_ip)
        return new_ip


class _FakeTaggedQuerySet:
    def __init__(self, object_ids):
        self._object_ids = object_ids

    def values_list(self, field_name, flat=False):
        assert field_name == "object_id"
        assert flat is True
        return list(self._object_ids)


class _FakeTaggedItemManager:
    def __init__(self, managed_ids):
        self._managed_ids = set(managed_ids)

    def filter(self, **kwargs):
        object_ids = kwargs.get("object_id__in", [])
        return _FakeTaggedQuerySet([object_id for object_id in object_ids if object_id in self._managed_ids])


class _FakeContentTypeManager:
    def get_for_model(self, model, for_concrete_model=False):
        return model


class _FakeVRF:
    def __init__(self, pk):
        self.pk = pk


def _configure_ip_sync_test(monkeypatch, existing_ips, managed_ids=()):
    ip_manager = _FakeIPManager(existing_ips)
    tagged_manager = _FakeTaggedItemManager(managed_ids)
    tagged_objects = []

    monkeypatch.setattr(_sync_mod, "ContentType", types.SimpleNamespace(objects=_FakeContentTypeManager()))
    monkeypatch.setattr(_sync_mod, "IPAddress", types.SimpleNamespace(objects=ip_manager))
    monkeypatch.setattr(_sync_mod, "TaggedItem", types.SimpleNamespace(objects=tagged_manager))
    monkeypatch.setattr(_sync_mod, "VMInterface", type("FakeVMInterface", (), {}))
    monkeypatch.setattr(_sync_mod, "_safe_add_tag", lambda obj, tag: tagged_objects.append((obj, tag.slug)))

    return ip_manager, tagged_objects


def test_sync_iface_ips_preserves_existing_ips_when_no_proxmox_ip_data(monkeypatch):
    existing_ip = _FakeIP("10.0.0.5/24", pk=1)
    ip_manager, tagged_objects = _configure_ip_sync_test(monkeypatch, [existing_ip], managed_ids={1})

    _sync_mod._sync_iface_ips(vm=object(), iface=types.SimpleNamespace(pk=10), ip_strings=[], vrf=None, tag=types.SimpleNamespace(slug="proxmox2netbox"))

    assert existing_ip.deleted is False
    assert ip_manager.created == []
    assert tagged_objects == []


def test_sync_iface_ips_deletes_only_managed_ips_when_authoritative_ips_exist(monkeypatch):
    managed_ip = _FakeIP("10.0.0.5/24", pk=1)
    manual_ip = _FakeIP("10.0.0.9/24", pk=2)
    ip_manager, tagged_objects = _configure_ip_sync_test(monkeypatch, [managed_ip, manual_ip], managed_ids={1})

    _sync_mod._sync_iface_ips(
        vm=object(),
        iface=types.SimpleNamespace(pk=10),
        ip_strings=["10.0.0.6/24"],
        vrf=None,
        tag=types.SimpleNamespace(slug="proxmox2netbox"),
    )

    assert managed_ip.deleted is True
    assert manual_ip.deleted is False
    assert [ip.address for ip in ip_manager.created] == ["10.0.0.6/24"]
    assert tagged_objects == [(ip_manager.created[0], "proxmox2netbox")]


def test_sync_iface_ips_can_keep_stale_managed_ips_when_pruning_disabled(monkeypatch):
    managed_ip = _FakeIP("10.0.0.5/24", pk=1)
    ip_manager, tagged_objects = _configure_ip_sync_test(monkeypatch, [managed_ip], managed_ids={1})

    _sync_mod._sync_iface_ips(
        vm=object(),
        iface=types.SimpleNamespace(pk=10),
        ip_strings=["10.0.0.6/24"],
        vrf=None,
        tag=types.SimpleNamespace(slug="proxmox2netbox"),
        prune_stale=False,
    )

    assert managed_ip.deleted is False
    assert [ip.address for ip in ip_manager.created] == ["10.0.0.6/24"]
    assert tagged_objects == [(ip_manager.created[0], "proxmox2netbox")]


def test_sync_iface_ips_updates_matching_ip_vrf_and_marks_it_managed(monkeypatch):
    existing_ip = _FakeIP("10.0.0.5/24", pk=1, vrf_id=None)
    _, tagged_objects = _configure_ip_sync_test(monkeypatch, [existing_ip], managed_ids={1})
    vrf = _FakeVRF(pk=7)

    _sync_mod._sync_iface_ips(
        vm=object(),
        iface=types.SimpleNamespace(pk=10),
        ip_strings=["10.0.0.5/24"],
        vrf=vrf,
        tag=types.SimpleNamespace(slug="proxmox2netbox"),
    )

    assert existing_ip.deleted is False
    assert existing_ip.vrf_id == 7
    assert tagged_objects == [(existing_ip, "proxmox2netbox")]


def test_run_sync_filters_disabled_endpoints(monkeypatch):
    enabled_endpoint = types.SimpleNamespace(
        name="enabled",
        last_synced=None,
        last_sync_status="",
        save=lambda update_fields=None: None,
    )
    disabled_endpoint = types.SimpleNamespace(name="disabled")

    class _EndpointQuerySet(list):
        def count(self):
            return len(self)

    class _EndpointManager:
        def filter(self, **kwargs):
            assert kwargs == {"sync_enabled": True}
            return _EndpointQuerySet([enabled_endpoint])

    seen = []

    def _connect(endpoint):
        seen.append(endpoint.name)
        return types.SimpleNamespace(endpoint=endpoint)

    monkeypatch.setattr(_sync_mod, "ProxmoxEndpoint", types.SimpleNamespace(objects=_EndpointManager()))
    monkeypatch.setattr(_sync_mod, "connect_endpoint", _connect)
    monkeypatch.setattr(
        _sync_mod,
        "_upsert_all_for_session",
        lambda session, sync_type: {"created_vms": 1},
    )

    result = _sync_mod._run_sync(_sync_mod.SyncTypeChoices.ALL)

    assert seen == ["enabled"]
    assert disabled_endpoint.name not in seen
    assert result["created_vms"] == 1
    assert result["endpoints"] == 1


def test_connect_endpoint_applies_request_timeout(monkeypatch):
    calls = []

    class _Version:
        @staticmethod
        def get():
            return {"version": "8.2"}

    class _Client:
        version = _Version()

    def _client_factory(host, **kwargs):
        calls.append((host, kwargs))
        return _Client()

    endpoint = types.SimpleNamespace(
        domain="pve.example.test",
        ip_address=None,
        token_name="sync",
        token_value="secret",
        password="",
        username="sync@pve",
        port=8006,
        verify_ssl=True,
    )
    monkeypatch.setattr(_sync_mod, "ProxmoxAPI", _client_factory)

    session = _sync_mod.connect_endpoint(endpoint)

    assert session.host == "pve.example.test"
    assert calls[0][1]["timeout"] == _sync_mod.PROXMOX_REQUEST_TIMEOUT
