# Django Imports
from django import forms
from django.forms import PasswordInput

# NetBox Imports
from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm
from utilities.forms.fields import CommentField, DynamicModelChoiceField
from dcim.models import DeviceType, Site
from ipam.models import IPAddress, VRF
from django.utils.translation import gettext as _

# Proxmox2NetBox Imports
from ..models import ProxmoxEndpoint, ProxmoxNodeTypeMapping
from ..choices import ProxmoxModeChoices


class ProxmoxEndpointForm(NetBoxModelForm):
    """
    Form for ProxmoxEndpoint model.
    It is used to CREATE and UPDATE ProxmoxEndpoint objects.
    """
    ip_address = DynamicModelChoiceField(
        queryset=IPAddress.objects.all(),
        help_text=_('Select a NetBox IP Address'),
        label=_('IP Address'),
        required=False
    )
    domain = forms.CharField(
        required=False,
        help_text=_('Domain name of the Proxmox Endpoint (Cluster). It will try using the DNS name provided in IP Address if it is not empty.'),
        label=_('Domain')
    )
    verify_ssl = forms.BooleanField(
        required=False,
        help_text=_('Choose or not to verify SSL certificate of the Proxmox Endpoint. Only use this if you are sure about the SSL certificate of the Proxmox Endpoint.'),
        label=_('Verify SSL')
    )
    netbox_site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        help_text=_('NetBox site for synced objects (nodes, VMs, clusters). If not set, a default site is used.'),
        label=_('NetBox Site'),
        required=False,
    )
    netbox_vrf = DynamicModelChoiceField(
        queryset=VRF.objects.all(),
        help_text=_('VRF for synced IP addresses. If not set, the global routing table is used.'),
        label=_('NetBox VRF'),
        required=False,
    )
    netbox_device_type = DynamicModelChoiceField(
        queryset=DeviceType.objects.all(),
        help_text=_('Device type for synced Proxmox nodes. If not set, one is auto-detected from CPU model or a generic type is used.'),
        label=_('Node Device Type'),
        required=False,
    )
    comments = CommentField()

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data is None:
            # NetBox 4.5 form stack may return None from parent clean().
            # In that case, validated field values are already in self.cleaned_data.
            cleaned_data = getattr(self, 'cleaned_data', {}) or {}

        # Secret widgets deliberately render empty on edits.  Treat an empty
        # submitted secret as "unchanged" so editing unrelated endpoint fields
        # neither exposes nor accidentally erases stored credentials.
        if self.instance.pk:
            for field_name in ('password', 'token_value'):
                if not (cleaned_data.get(field_name) or '').strip():
                    cleaned_data[field_name] = getattr(self.instance, field_name)

        password = (cleaned_data.get('password') or '').strip()
        token_name = (cleaned_data.get('token_name') or '').strip()
        token_value = (cleaned_data.get('token_value') or '').strip()

        if not password:
            if token_name and not token_value:
                self.add_error('token_value', _('Token Value is required when Token Name is set.'))
            elif token_value and not token_name:
                self.add_error('token_name', _('Token Name is required when Token Value is set.'))
            elif not (token_name and token_value):
                raise forms.ValidationError(
                    _('Provide either username/password or username with both Token Name and Token Value.')
                )

        return cleaned_data
    
    class Meta:
        model = ProxmoxEndpoint
        fields = (
            'name', 'ip_address', 'domain', 'port', 'username',
            'password', 'token_name', 'token_value', 'verify_ssl',
            'netbox_site', 'netbox_vrf', 'netbox_device_type',
            'sync_enabled', 'sync_nodes', 'sync_qemu_vms', 'sync_lxc_containers',
            'sync_vm_interfaces', 'sync_vm_ips', 'sync_guest_agent_ips',
            'sync_vm_disks', 'prune_stale_vm_interfaces', 'prune_stale_vm_ips',
            'prune_stale_vm_disks',
            'tags',
        )
        widgets = {
            'password': PasswordInput(render_value=False),
            'token_value': PasswordInput(render_value=False),
        }


class ProxmoxEndpointFilterForm(NetBoxModelFilterSetForm):
    """
    Filter form for ProxmoxEndpoint model.
    It is used in the ProxmoxEndpointListView.
    """
    
    model = ProxmoxEndpoint
    name = forms.CharField(
        required=False
    )
    ip_address = forms.ModelMultipleChoiceField(
        queryset=IPAddress.objects.all(),
        required=False,
        help_text='Select IP Address'
    )
    mode = forms.MultipleChoiceField(
        choices=ProxmoxModeChoices,
        required=False
    )
    sync_enabled = forms.NullBooleanField(
        required=False,
        label=_('Sync Enabled'),
    )
    sync_nodes = forms.NullBooleanField(
        required=False,
        label=_('Sync Nodes'),
    )
    sync_qemu_vms = forms.NullBooleanField(
        required=False,
        label=_('Sync QEMU VMs'),
    )
    sync_lxc_containers = forms.NullBooleanField(
        required=False,
        label=_('Sync LXC Containers'),
    )


class ProxmoxNodeTypeMappingForm(NetBoxModelForm):
    endpoint = forms.ModelChoiceField(
        queryset=ProxmoxEndpoint.objects.select_related('ip_address'),
        label=_('Proxmox Endpoint'),
    )
    device_type = DynamicModelChoiceField(
        queryset=DeviceType.objects.all(),
        label=_('Device Type'),
        help_text=_('Device type to assign to this node during sync.'),
    )

    class Meta:
        model = ProxmoxNodeTypeMapping
        fields = ('endpoint', 'node_name', 'custom_name', 'device_type', 'tags')


class ProxmoxNodeTypeMappingFilterForm(NetBoxModelFilterSetForm):
    model = ProxmoxNodeTypeMapping
    node_name = forms.CharField(required=False, label=_('Node Name'))
    endpoint = forms.ModelChoiceField(
        queryset=ProxmoxEndpoint.objects.select_related('ip_address'),
        required=False,
        label=_('Proxmox Endpoint'),
    )
