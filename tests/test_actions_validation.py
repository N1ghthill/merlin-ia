from executor.actions import build_action_registry
from executor.config import Config


def test_invalid_service_name_rejected():
    actions = build_action_registry(Config())
    ok, _ = actions["read.service_status"].validate({"service": "nginx;rm -rf /"}, Config())
    assert not ok


def test_journal_lines_bounds():
    actions = build_action_registry(Config())
    ok_low, _ = actions["read.journalctl"].validate({"service": "ssh", "lines": 0}, Config())
    ok_high, _ = actions["read.journalctl"].validate({"service": "ssh", "lines": 9999}, Config())
    assert not ok_low
    assert not ok_high


def test_packages_manager_auto_ok():
    actions = build_action_registry(Config())
    ok, _ = actions["read.packages"].validate({"manager": "auto"}, Config())
    assert ok


def test_service_control_invalid_operation():
    actions = build_action_registry(Config())
    ok, _ = actions["service.control"].validate({"service": "nginx", "operation": "reload"}, Config())
    assert not ok


def test_pkg_install_invalid_package():
    actions = build_action_registry(Config())
    ok, _ = actions["pkg.install"].validate({"packages": ["nginx;rm -rf /"]}, Config())
    assert not ok


def test_no_args_actions_reject_unknown():
    actions = build_action_registry(Config())
    ok, _ = actions["read.df"].validate({"unexpected": "x"}, Config())
    assert not ok
