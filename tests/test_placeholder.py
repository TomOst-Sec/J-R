"""Placeholder test to verify project setup."""


def test_import_argus() -> None:
    """Verify argus package is importable and has correct version."""
    import argus

    assert argus.__version__ == "0.1.0"
