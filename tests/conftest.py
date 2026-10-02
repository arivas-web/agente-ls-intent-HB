import pytest
from vt.config import load


@pytest.fixture(scope="session")
def url_cfg():
    return load("url_scoring")


@pytest.fixture(scope="session")
def fit_cfg():
    return load("fit")


@pytest.fixture(scope="session")
def eng_cfg():
    return load("engagement")


@pytest.fixture(scope="session")
def int_cfg():
    return load("intent")


@pytest.fixture(scope="session")
def persona_cfg():
    return load("persona")
