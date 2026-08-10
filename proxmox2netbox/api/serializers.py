from rest_framework import serializers

from netbox.api.serializers import NetBoxModelSerializer
from netbox.api.fields import ContentTypeField
from extras.api.serializers import TagSerializer
from ipam.api.serializers import IPAddressSerializer
from proxmox2netbox.models import (
    ProxmoxEndpoint,
    SyncProcess,
)
from proxmox2netbox.choices import (
    SyncTypeChoices,
    SyncStatusChoices,
)
# JournalEntryKindChoices is typically defined in the choices module of the NetBox codebase.
# Since we are dealing with a serializer related to journal entries, it is likely imported from extras.choices.
from extras.choices import JournalEntryKindChoices

from extras.models import JournalEntry
from django.contrib.contenttypes.models import ContentType

class SyncProcessSerializer(NetBoxModelSerializer):
    """
    Serializer for SyncProcess model.
    
    This serializer handles the conversion of SyncProcess objects to/from JSON.
    It extends NetBoxModelSerializer to support NetBox's standard features like tags and custom fields.
    
    Attributes:
        url: HyperlinkedIdentityField for the object's detail view
        sync_type: ChoiceField for sync process type
        status: ChoiceField for sync process status
        runtime: FloatField for process duration
        started_at: DateTimeField for process start time
        completed_at: DateTimeField for process completion time
        tags: TagSerializer for associated tags
        
    Fields:
        - id: Unique identifier
        - url: API endpoint URL
        - display: Human-readable display string
        - name: Process name
        - sync_type: Type of sync process
        - status: Current status
        - started_at: Start timestamp
        - completed_at: Completion timestamp
        - runtime: Process duration in seconds
        - tags: Associated tags
        - created: Creation timestamp
        - last_updated: Last update timestamp
    """
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:proxmox2netbox-api:syncprocess-detail',
    )
    sync_type = serializers.ChoiceField(choices=SyncTypeChoices)
    status = serializers.ChoiceField(choices=SyncStatusChoices)
    runtime = serializers.FloatField(required=False, allow_null=True)
    started_at = serializers.DateTimeField(required=False, allow_null=True)
    completed_at = serializers.DateTimeField(required=False, allow_null=True)
    tags = TagSerializer(many=True, required=False, nested=True)
    
    class Meta:
        model = SyncProcess
        fields = (
            'id', 'url', 'display', 'name', 'sync_type', 'status', 'started_at', 'completed_at',
            'runtime', 'tags', 'created', 'last_updated',
        )

class ProxmoxEndpointSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:proxmox2netbox-api:endpoints:proxmox-endpoint-detail',
    )
    ip_address = IPAddressSerializer()
    domain = serializers.CharField(required=False, allow_null=True)
    # Credentials are write-only: accepted on create/update but never returned in responses.
    password = serializers.CharField(required=False, allow_null=True, write_only=True)
    token_value = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = ProxmoxEndpoint
        fields = (
            'id', 'url', 'display', 'name', 'ip_address', 'domain', 'port',
            'token_name', 'token_value', 'username', 'password', 'verify_ssl',
            'mode', 'version', 'repoid',
            'netbox_site', 'netbox_vrf', 'netbox_device_type',
            'sync_enabled', 'sync_nodes', 'sync_qemu_vms', 'sync_lxc_containers',
            'sync_vm_interfaces', 'sync_vm_ips', 'sync_guest_agent_ips',
            'sync_vm_disks', 'prune_stale_vm_interfaces', 'prune_stale_vm_ips',
            'prune_stale_vm_disks',
            'tags', 'custom_fields', 'created', 'last_updated',
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)

        instance = getattr(self, 'instance', None)

        def get_value(field_name):
            if field_name in attrs:
                return (attrs.get(field_name) or '').strip()
            if instance is not None:
                return (getattr(instance, field_name, '') or '').strip()
            return ''

        password = get_value('password')
        token_name = get_value('token_name')
        token_value = get_value('token_value')

        if not password:
            if token_name and not token_value:
                raise serializers.ValidationError({'token_value': 'Token Value is required when Token Name is set.'})  # nosec B105

            if token_value and not token_name:
                raise serializers.ValidationError({'token_name': 'Token Name is required when Token Value is set.'})  # nosec B105

            if not (token_name and token_value):
                raise serializers.ValidationError(
                    'Provide either username/password or username with both Token Name and Token Value.'
                )

        return attrs

class JournalEntrySerializer(NetBoxModelSerializer):
    """
    Serializer for JournalEntry model.
    
    This serializer handles the conversion of JournalEntry objects to/from JSON,
    providing a standardized way to represent journal entries in the API.
    It extends NetBoxModelSerializer to support NetBox's standard features.
    
    Attributes:
        url: HyperlinkedIdentityField for the object's detail view
        assigned_object_type: ContentTypeField for the associated object type
        assigned_object_id: IntegerField for the associated object ID
        kind: ChoiceField for the entry type (info, success, warning, error)
        comments: CharField for the entry content
        tags: TagSerializer for associated tags
        
    Fields:
        - id: Unique identifier
        - url: API endpoint URL
        - display: Human-readable display string
        - assigned_object_type: Type of associated object
        - assigned_object_id: ID of associated object
        - kind: Entry type
        - comments: Entry content
        - tags: Associated tags
        - created: Creation timestamp
        - last_updated: Last update timestamp
        
    Example JSON:
        {
            "id": 1,
            "url": "/api/plugins/proxmox2netbox/journal-entries/1/",
            "display": "Info: Sync process started",
            "assigned_object_type": "proxmox2netbox.syncprocess",
            "assigned_object_id": 1,
            "kind": "info",
            "comments": "Sync process started",
            "tags": [],
            "created": "2024-01-01T00:00:00Z",
            "last_updated": "2024-01-01T00:00:00Z"
        }
    """
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:proxmox2netbox-api:journalentry-detail',
    )
    assigned_object_type = ContentTypeField(
        queryset=ContentType.objects.filter(
            app_label='proxmox2netbox',
            model='syncprocess',
        ),
        required=True,
    )
    assigned_object_id = serializers.IntegerField(required=True)
    kind = serializers.ChoiceField(choices=JournalEntryKindChoices)
    comments = serializers.CharField()
    tags = TagSerializer(many=True, required=False, nested=True)
    
    class Meta:
        model = JournalEntry
        fields = (
            'id', 'url', 'display', 'assigned_object_type', 'assigned_object_id',
            'kind', 'comments',
            'tags', 'created', 'last_updated',
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        object_type = attrs.get('assigned_object_type')
        object_id = attrs.get('assigned_object_id')
        if object_type is not None and (
            object_type.app_label != 'proxmox2netbox' or object_type.model != 'syncprocess'
        ):
            raise serializers.ValidationError({
                'assigned_object_type': 'Journal entries must belong to a sync process.'
            })
        if object_id is not None and not SyncProcess.objects.filter(pk=object_id).exists():
            raise serializers.ValidationError({
                'assigned_object_id': 'The specified sync process does not exist.'
            })
        return attrs
