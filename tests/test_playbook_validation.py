from executor.actions import build_action_registry
from executor.config import Config


def test_playbook_validation_allows_inside_path(tmp_path):
    playbooks_dir = tmp_path / "playbooks"
    playbooks_dir.mkdir()
    playbook = playbooks_dir / "test.yml"
    playbook.write_text("- hosts: localhost\n  tasks: []\n", encoding="utf-8")

    cfg = Config(playbooks_dir=str(playbooks_dir))
    actions = build_action_registry(cfg)
    ok, err = actions["ansible.playbook"].validate({"playbook": str(playbook)}, cfg)
    assert ok, err


def test_playbook_validation_rejects_outside_path(tmp_path):
    playbooks_dir = tmp_path / "playbooks"
    playbooks_dir.mkdir()
    outside = tmp_path / "outside.yml"
    outside.write_text("- hosts: localhost\n  tasks: []\n", encoding="utf-8")

    cfg = Config(playbooks_dir=str(playbooks_dir))
    actions = build_action_registry(cfg)
    ok, err = actions["ansible.playbook"].validate({"playbook": str(outside)}, cfg)
    assert not ok
