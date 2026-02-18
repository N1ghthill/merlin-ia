from executor.acl import is_action_allowed


def test_read_allowed_without_write():
    assert is_action_allowed("read.os_release", allow_write_actions=False)


def test_write_blocked_without_flag():
    assert not is_action_allowed("pkg.install", allow_write_actions=False)


def test_write_allowed_with_flag():
    assert is_action_allowed("pkg.install", allow_write_actions=True)


def test_unknown_action_blocked():
    assert not is_action_allowed("unknown.action", allow_write_actions=False)
