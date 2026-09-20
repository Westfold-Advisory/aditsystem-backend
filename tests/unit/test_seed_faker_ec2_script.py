from pathlib import Path


def test_faker_ec2_script_is_development_only_and_invokes_cli() -> None:
    script = Path("scripts/seed-faker-development-ec2.sh").read_text(encoding="utf-8")
    assert '"$app_env" != "development"' in script
    assert "aditsystem-seed-faker" in script
    assert "BOOTSTRAP_PASSWORD_SECRET_ID" in script
    assert "set -x" not in script


def test_faker_ssm_script_requires_explicit_confirmation() -> None:
    script = Path("scripts/seed-faker-development-ssm.sh").read_text(encoding="utf-8")
    assert "SEED_DEVELOPMENT_FAKER" in script
    assert "seed-faker-development-ec2.sh" in script
