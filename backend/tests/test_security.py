from app.auth.security import hash_password, verify_password, ROLE_PERMISSIONS


def test_argon2_password_hash_verifies():
    hashed = hash_password("test-password-123")
    assert hashed != "test-password-123"
    assert verify_password("test-password-123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_read_only_role_cannot_investigate():
    assert "read" in ROLE_PERMISSIONS["read_only_auditor"]
    assert "investigate" not in ROLE_PERMISSIONS["read_only_auditor"]
