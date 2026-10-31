"""Environment and Dependency Verification Test.

Validates that all core libraries (FastAPI, Pandas, NumPy, Scikit-learn,
Joblib, SQLite, Pydantic, Matplotlib, Seaborn) are installed and importable.
"""

import sys
import sqlite3
import pytest


def test_core_dependencies():
    """Verify all mandatory backend and ML dependencies can be imported."""
    import fastapi
    import uvicorn
    import pydantic
    import sklearn
    import pandas
    import numpy
    import joblib

    assert fastapi.__version__ is not None
    assert pydantic.__version__ is not None
    assert sklearn.__version__ is not None
    assert pandas.__version__ is not None
    assert numpy.__version__ is not None
    assert joblib.__version__ is not None


def test_visualization_dependencies():
    """Verify matplotlib and seaborn packages."""
    import matplotlib
    import seaborn

    assert matplotlib.__version__ is not None
    assert seaborn.__version__ is not None


def test_sqlite_support():
    """Verify built-in SQLite3 engine is operational."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("SELECT sqlite_version();")
    version = cursor.fetchone()[0]
    conn.close()
    assert version is not None


def test_optional_xgboost():
    """Verify optional XGBoost dependency."""
    try:
        import xgboost
        assert xgboost.__version__ is not None
        print(f"XGBoost installed: {xgboost.__version__}")
    except ImportError:
        pytest.skip("Optional dependency XGBoost is not installed.")
