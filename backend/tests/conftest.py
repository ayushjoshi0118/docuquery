import os
import sys
import shutil
import tempfile
import pytest

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pymupdf
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Force test configuration
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["STORAGE_BACKEND"] = "filesystem"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "True"
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["SECRET_KEY"] = "test-secret-key-for-docuquery-unit-testing-32-chars-long"

from docuquery.config import settings
settings.ENVIRONMENT = "test"
settings.DATABASE_URL = "sqlite:///:memory:"
settings.STORAGE_BACKEND = "filesystem"
settings.CELERY_TASK_ALWAYS_EAGER = True
settings.EMBEDDING_PROVIDER = "mock"
settings.LLM_PROVIDER = "mock"

# Setup temporary storage directory
temp_storage_dir = tempfile.mkdtemp()
settings.STORAGE_LOCAL_DIR = temp_storage_dir

from docuquery.database import Base, get_db, SessionLocal, engine
from docuquery.main import app
from docuquery.services.storage_service import FilesystemStorageService
import docuquery.services.storage_service as storage_module
storage_module._storage_instance = FilesystemStorageService(base_dir=temp_storage_dir)

from docuquery.core.rate_limiter import auth_rate_limiter
auth_rate_limiter.enabled = False
from docuquery.services.token_blacklist import clear_blacklist

# Create in-memory SQLite test engine
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocal.configure(bind=test_engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    shutil.rmtree(temp_storage_dir, ignore_errors=True)


@pytest.fixture
def db():
    clear_blacklist()
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def create_pdf_bytes():
    """Helper fixture to generate in-memory PDFs with specific pages and text."""
    def _generator(pages_text: list[str], encrypt_password: str = None) -> bytes:
        doc = pymupdf.open()
        for text in pages_text:
            page = doc.new_page()
            rect = pymupdf.Rect(50, 50, 550, 750)
            page.insert_textbox(rect, text, fontsize=11)
        if encrypt_password:
            # Encrypt document
            doc.save(
                "temp.pdf",
                encryption=pymupdf.PDF_ENCRYPT_AES_256,
                owner_pw=encrypt_password,
                user_pw=encrypt_password,
            )
            doc.close()
            with open("temp.pdf", "rb") as f:
                data = f.read()
            os.remove("temp.pdf")
            return data

        data = doc.write()
        doc.close()
        return data

    return _generator


@pytest.fixture
def user_a_tokens(client):
    email = "user_a@example.com"
    password = "SecurePassword123!"
    client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "User Alpha"})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()


@pytest.fixture
def auth_headers_user_a(user_a_tokens):
    return {"Authorization": f"Bearer {user_a_tokens['access_token']}"}


@pytest.fixture
def user_b_tokens(client):
    email = "user_b@example.com"
    password = "SecurePassword456!"
    client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "User Beta"})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()


@pytest.fixture
def auth_headers_user_b(user_b_tokens):
    return {"Authorization": f"Bearer {user_b_tokens['access_token']}"}
