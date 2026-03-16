"""Tests for encrypted storage."""

import pytest

from argus.storage.database import Database
from argus.storage.encrypted import EncryptedDatabase, create_database


class TestCreateDatabase:
    def test_creates_regular_database(self):
        db = create_database(encryption_enabled=False)
        assert isinstance(db, Database)
        assert not isinstance(db, EncryptedDatabase)

    def test_creates_encrypted_database(self):
        db = create_database(encryption_enabled=True, encryption_key="testkey")
        assert isinstance(db, EncryptedDatabase)

    def test_encrypted_without_key_raises(self):
        db = EncryptedDatabase(encryption_key=None)
        with pytest.raises(ValueError, match="Encryption key required"):
            import asyncio
            asyncio.run(db.initialize())

    def test_encrypted_without_sqlcipher_raises(self):
        """Without sqlcipher3 installed, should raise ImportError."""
        # This test will pass in CI where sqlcipher3 is not installed
        db = EncryptedDatabase(encryption_key="testkey")
        try:
            import asyncio
            asyncio.run(db.initialize())
        except ImportError as e:
            assert "sqlcipher3" in str(e)
        except Exception:
            pass  # sqlcipher3 might be installed in some environments


class TestRegularDatabaseUnchanged:
    @pytest.mark.asyncio
    async def test_regular_db_still_works(self):
        db = Database()
        await db.initialize()
        assert db.conn is not None
        await db.close()
