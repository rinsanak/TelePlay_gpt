"""Run with: python -m unittest discover -s tests -v (from backend)."""
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

# No Telegram connection or real credentials are used by these tests.
os.environ.update(TELEGRAM_API_ID="1", TELEGRAM_API_HASH="test",
    TELEGRAM_BOT_TOKEN="test", TELEGRAM_STORAGE_CHANNEL_ID="-1001",
    DATABASE_URL="sqlite+aiosqlite:///" + tempfile.gettempdir() + "/teleplay-tests.db",
    JWT_SECRET="test-only-secret-not-for-production")

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database import Base
from app.models import User, File
from app.routers.files import get_subtitles
from app.routers.streaming import external_player_link, external_stream
from app.auth import verify_token_payload, create_access_token
from jose import jwt
from app.subtitle_matching import rank_subtitles


class MatchingTests(unittest.TestCase):
    def test_punctuation_and_case(self):
        files = [SimpleNamespace(file_name=n) for n in ["Other.srt", "MOVIE_Name.2026.SSA"]]
        self.assertEqual(rank_subtitles("Movie Name 2026.mkv", files)[0], files[1])

    def test_ties_preserve_recency(self):
        files = [SimpleNamespace(file_name="Movie.srt"), SimpleNamespace(file_name="Movie.vtt")]
        self.assertEqual(rank_subtitles("Movie.mp4", files), files)


class PlayerApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.db = async_sessionmaker(self.engine, expire_on_commit=False)()
        self.user = User(telegram_id=1)
        self.other = User(telegram_id=2)
        self.db.add_all([self.user, self.other])
        await self.db.flush()
        self.video = await self.add_file("Movie 2026.mkv", 0)
        # Old exact match must not displace any of the four latest subtitles.
        await self.add_file("Movie 2026.srt", 1)
        await self.add_file("Other.srt", 2)
        await self.add_file("Different.vtt", 3)
        await self.add_file("Movie.2026.ASS", 4)
        await self.add_file("New.ssa", 5)
        await self.add_file("Not-a-subtitle.srt.exe", 6)
        await self.add_file("Private.srt", 7, self.other)
        await self.db.commit()

    async def add_file(self, name, index, user=None):
        file = File(user_id=(user or self.user).id, file_id=str(index),
            file_unique_id=str(index), channel_message_id=index, file_name=name,
            file_size=1234, file_type="document", created_at=datetime(2026, 1, 1) + timedelta(seconds=index))
        self.db.add(file)
        await self.db.flush()
        return file

    async def asyncTearDown(self):
        await self.db.close()
        await self.engine.dispose()

    async def test_latest_four_then_rank_with_size(self):
        result = await get_subtitles(self.video.id, self.db, self.user)
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0].file_name, "Movie.2026.ASS")
        self.assertEqual({f.file_name for f in result}, {"Other.srt", "Different.vtt", "Movie.2026.ASS", "New.ssa"})
        self.assertTrue(all(f.file_size == 1234 for f in result))

    async def test_subtitles_reject_other_users_video(self):
        with self.assertRaises(HTTPException) as error:
            await get_subtitles(self.video.id, self.db, self.other)
        self.assertEqual(error.exception.status_code, 404)

    async def test_external_link_scoped_and_does_not_publish(self):
        result = await external_player_link(self.video.id, self.db, self.user)
        token = result["path"].rsplit("/", 1)[1]
        payload = verify_token_payload(token, "external_stream")
        self.assertEqual(payload["file_id"], self.video.id)
        self.assertIsNone(verify_token_payload(token))
        self.assertIsNone(self.video.public_hash)
        with patch("app.routers.streaming.stream_file", new_callable=AsyncMock) as stream:
            await external_stream(token, None, self.db)
            self.assertEqual(stream.call_args.args[0], self.video.id)
        self.user.auth_version += 1
        await self.db.commit()
        with self.assertRaises(HTTPException):
            await external_stream(token, None, self.db)

    async def test_external_link_rejects_other_user(self):
        with self.assertRaises(HTTPException):
            await external_player_link(self.video.id, self.db, self.other)

    async def test_external_stream_rejects_access_token_and_invalid_token(self):
        for token in ("invalid", create_access_token(1)):
            with self.assertRaises(HTTPException):
                await external_stream(token, None, self.db)

    async def test_external_stream_rejects_expired_link(self):
        token = jwt.encode({"type": "external_stream", "file_id": self.video.id,
            "sub": str(self.user.id), "ver": self.user.auth_version,
            "exp": datetime.utcnow() - timedelta(seconds=1)},
            os.environ["JWT_SECRET"], algorithm="HS256")
        with self.assertRaises(HTTPException) as error:
            await external_stream(token, None, self.db)
        self.assertEqual(error.exception.status_code, 401)

    async def test_empty_subtitle_list(self):
        video = await self.add_file("No subtitles.mkv", 8, self.other)
        from sqlalchemy import delete
        await self.db.execute(delete(File).where(File.user_id == self.other.id, File.id != video.id))
        await self.db.commit()
        self.assertEqual(await get_subtitles(video.id, self.db, self.other), [])
