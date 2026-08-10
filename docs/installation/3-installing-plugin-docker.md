# Installing the Plugin using Docker

For `netbox-docker`, install this plugin through the requirements mechanism so it survives rebuilds.

## 1. Add package to local requirements

Add this line to your `local_requirements.txt` used by your deployment:

```text
proxmox2netbox==1.2.12
```

## 2. Enable plugin

In NetBox config (`plugins.py` or `configuration.py` depending on your setup):

```python
PLUGINS = ["proxmox2netbox"]
```

## 3. Rebuild/restart and run migrations

After container rebuild/start, run:

```bash
python3 manage.py migrate
python3 manage.py collectstatic --no-input
```

No external backend service is required.
