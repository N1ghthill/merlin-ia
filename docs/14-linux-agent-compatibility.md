# Linux Agent Compatibility Matrix

This matrix summarizes supported platforms and feature constraints.

## Operating Systems
- Linux only.
- systemd is required for `service.control` actions (systemctl).

## Package Managers
- Debian/Ubuntu: `apt-get` / `dpkg -l`
- RHEL/Fedora: `dnf` or `yum` / `rpm -qa`
- Arch: `pacman`

## Features
- `read.*`: supported on all distros above.
- `service.control`: requires systemd.
- `pkg.install`: requires an available package manager.
- `ansible.playbook`: requires `ansible-playbook` and allowlisted playbooks directory.

## Notes
- Containers without systemd may support `read.*` but not `service.control`.
- For `ansible.playbook`, enable `ANSIBLE_PREVIEW_EXECUTE=true` only on test systems.
