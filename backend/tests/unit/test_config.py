def test_settings_reads_jwt_secret_from_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "my-test-secret")
    from app.core.config import Settings

    s = Settings()
    assert s.JWT_SECRET == "my-test-secret"


def test_settings_defaults_are_sane():
    from app.core.config import Settings

    s = Settings()
    assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 15
    assert s.JWT_ALGORITHM == "HS256"
    assert s.BCRYPT_ROUNDS == 12
    assert s.API_V1_PREFIX == "/api/v1"
