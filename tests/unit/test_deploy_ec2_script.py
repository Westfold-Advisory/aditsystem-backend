from pathlib import Path


def test_deploy_runtime_env_propagates_aws_region_to_boto3() -> None:
    script = Path("scripts/deploy-ec2.sh").read_text(encoding="utf-8")

    assert '"AWS_REGION": os.environ["AWS_REGION"]' in script
    assert '"AWS_DEFAULT_REGION": os.environ["AWS_REGION"]' in script
