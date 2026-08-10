# Installation

## Install package

```bash
pip install proxmox2netbox
```

For `netbox-docker`, also add it to `local_requirements.txt` so it persists after rebuild/redeploy:

```text
proxmox2netbox==1.2.12
```

## Enable plugin in NetBox

Add to `configuration.py`:

```python
PLUGINS = ["proxmox2netbox"]
```

## Apply plugin migration and static

```bash
python manage.py migrate
python manage.py collectstatic --no-input
```

## Open plugin UI

`Plugins -> Proxmox2NetBox`
