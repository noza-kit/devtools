from gazemouse.safety import SafetyMonitor


def test_active_by_default():
    monitor = SafetyMonitor()
    assert monitor.is_active is True


def test_face_lost_deactivates():
    monitor = SafetyMonitor()
    monitor.update_face_visibility(False)
    assert monitor.is_active is False


def test_face_regained_reactivates():
    monitor = SafetyMonitor()
    monitor.update_face_visibility(False)
    monitor.update_face_visibility(True)
    assert monitor.is_active is True


def test_kill_switch_deactivates():
    monitor = SafetyMonitor()
    monitor.kill_switch()
    assert monitor.is_active is False


def test_kill_switch_survives_face_returning():
    """A face reappearing must NOT silently undo an explicit kill
    switch -- the user chose to turn gazemouse off."""
    monitor = SafetyMonitor()
    monitor.kill_switch()
    monitor.update_face_visibility(False)
    monitor.update_face_visibility(True)
    assert monitor.is_active is False


def test_re_enable_after_kill_switch():
    monitor = SafetyMonitor()
    monitor.kill_switch()
    monitor.re_enable()
    assert monitor.is_active is True


def test_toggle_flips_state():
    monitor = SafetyMonitor()
    assert monitor.toggle() is False
    assert monitor.is_active is False
    assert monitor.toggle() is True
    assert monitor.is_active is True


def test_both_conditions_required_for_active():
    monitor = SafetyMonitor()
    monitor.kill_switch()
    monitor.update_face_visibility(False)
    monitor.re_enable()
    assert monitor.is_active is False  # still no face
    monitor.update_face_visibility(True)
    assert monitor.is_active is True
