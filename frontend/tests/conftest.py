import pytest

# pytest-asyncio strict mode conflicts with pytest-playwright sync API.
# Override asyncio_mode to auto for this test package only.
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
