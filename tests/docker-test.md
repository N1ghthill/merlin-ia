# Docker Validation (Basic)

This is a minimal validation flow to avoid touching the real host.

## Start a container
```bash
docker run -it --rm --privileged --name test-ubuntu ubuntu:22.04 /bin/bash
```

## Inside the container
```bash
apt-get update
apt-get install -y python3 python3-pip ansible

# copy executor code into the container or mount it
# then run:
python3 /opt/linux-agent/executor/executor.py
```

## Smoke tests
- `GET /whoami`
- `POST /run` for `read.*` actions with `dry_run=true`
- `pkg.install` (dry-run first, then execute) inside the container

For deeper validation, use Vagrant boxes (Ubuntu/Debian + CentOS/RHEL).

