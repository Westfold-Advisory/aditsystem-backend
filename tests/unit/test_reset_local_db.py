from pathlib import Path


def test_reset_script_requires_explicit_confirmation_and_local_environment() -> None:
    script = Path("scripts/reset-local-db.sh").read_text(encoding="utf-8")
    assert "--confirm-local-reset" in script
    assert '[[ "$app_env" != "local" ]]' in script
    assert "docker compose --env-file" in script
    assert "down --volumes --remove-orphans" in script
    assert "production" not in script.lower()
