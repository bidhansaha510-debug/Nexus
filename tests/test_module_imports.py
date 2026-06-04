import importlib
import pytest
from conftest import ALL_MODULES

@pytest.mark.slow
@pytest.mark.parametrize("module_name", ALL_MODULES)
def test_import_module(module_name):
    """Test that all key modules can be imported without error."""
    importlib.import_module(module_name)
