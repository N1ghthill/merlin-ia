from merlin.handlers.linux_intents import detect_intent


def test_detect_diagnose():
    intent = detect_intent("Verificar status do nginx e logs dos últimos 50 eventos")
    assert intent and intent["intent"] == "diagnose"
    assert intent["service"] == "nginx"
    assert intent["lines"] == 50


def test_detect_install():
    intent = detect_intent("Instalar nginx usando apt")
    assert intent and intent["intent"] == "install"
    assert intent["service"] == "nginx"
    assert intent["manager"] == "apt"


def test_detect_harden_ssh():
    intent = detect_intent("Aplicar hardening no ssh")
    assert intent and intent["intent"] == "harden"
    assert intent["target"] == "ssh"


def test_detect_harden_firewall():
    intent = detect_intent("Configurar firewall com ufw")
    assert intent and intent["intent"] == "harden"
    assert intent["target"] == "firewall"

