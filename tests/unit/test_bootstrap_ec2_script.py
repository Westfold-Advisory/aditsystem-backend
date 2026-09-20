from pathlib import Path


def test_ec2_bootstrap_script_is_development_only_and_does_not_expose_secret() -> None:
    script = Path("scripts/bootstrap-development-ec2.sh").read_text(encoding="utf-8")
    assert '"$app_env" != "development"' in script
    assert "BOOTSTRAP_PASSWORD_SECRET_ID" in script
    assert "aditsystem-bootstrap-admin" in script
    assert "set -x" not in script
    assert "get-secret-value" not in script
