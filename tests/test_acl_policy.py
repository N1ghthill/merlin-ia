from executor.acl import load_acl_policy, is_action_allowed
from executor.config import Config
import json
from executor.acl import parse_id_list


def test_acl_policy_override(tmp_path):
    policy = {
        "read.os_release": {"allow_read": False, "allow_write": False},
        "pkg.install": {"allow_read": False, "allow_write": False},
    }
    policy_path = tmp_path / "acl.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    cfg = Config()
    loaded = load_acl_policy(str(policy_path))
    assert not is_action_allowed("read.os_release", cfg.allow_write_actions, loaded)
    assert not is_action_allowed("pkg.install", cfg.allow_write_actions, loaded)


def test_parse_id_list():
    assert parse_id_list("100,200") == {100, 200}
    assert parse_id_list("  ") == set()
