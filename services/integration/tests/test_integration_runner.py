def test_integration_runner_returns_zero():
    """Run the existing integration runner and assert it exits successfully.

    This leverages `microservice/integration/test_runner.py::run_integration` which
    starts a mock HTTP sink and the three services, exercises flows, then tears down.
    """
    # ensure repo root is importable when running this test in isolation
    import sys
    from pathlib import Path
    repo_root = str(Path(__file__).resolve().parents[3])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    from microservice.integration import test_runner as tr

    code = tr.run_integration()
    assert code == 0, f"integration runner exited with non-zero code: {code}"
