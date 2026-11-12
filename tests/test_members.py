import tempfile
import unittest
from pathlib import Path

from bson import ObjectId

from webapp import app as default_app, create_app


default_app.extensions["mongodb_client"].close()


class FakeCursor:
    def __init__(self, documents):
        self.documents = list(documents)

    def sort(self, field, direction=1):
        self.documents.sort(key=lambda document: document.get(field, ""), reverse=direction < 0)
        return self

    def __iter__(self):
        return iter(self.documents)


class FakeUsersCollection:
    def __init__(self, users):
        self.users = users

    def find(self, _query, _projection=None):
        return FakeCursor(self.users)

    def find_one(self, query, _projection=None):
        return next((user for user in self.users if all(user.get(key) == value for key, value in query.items())), None)


class FakeSongsCollection:
    def __init__(self, songs):
        self.songs = songs

    def aggregate(self, _pipeline):
        counts = {}
        for song in self.songs:
            owner_id = song.get("user_id")
            counts[owner_id] = counts.get(owner_id, 0) + 1
        return [{"_id": owner_id, "count": count} for owner_id, count in counts.items()]

    def find(self, query):
        return FakeCursor(
            song for song in self.songs
            if all(song.get(key) == value for key, value in query.items())
        )

    def find_one(self, query, _projection=None):
        return next((song for song in self.songs if all(song.get(key) == value for key, value in query.items())), None)


class MemberRoutesTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.owner_id = ObjectId()
        self.member_id = ObjectId()
        self.cover_name = "member-cover.png"
        self.app.extensions["users_collection"] = FakeUsersCollection([
            {"_id": self.owner_id, "username": "Owner", "password_hash": "not returned"},
            {"_id": self.member_id, "username": "Member", "password_hash": "not returned"},
        ])
        self.app.extensions["songs_collection"] = FakeSongsCollection([
            {
                "_id": ObjectId(),
                "user_id": str(self.member_id),
                "nombre": "Song",
                "artista": "Artist",
                "genero": "Pop",
                "log": "A public note",
                "calificacion": 4.5,
                "imagen": self.cover_name,
            },
        ])
        self.image_directory = tempfile.TemporaryDirectory()
        self.app.config["IMAGE_FOLDER"] = Path(self.image_directory.name)
        (Path(self.image_directory.name) / self.cover_name).write_bytes(b"cover")
        self.client = self.app.test_client()

    def tearDown(self):
        self.image_directory.cleanup()
        self.app.extensions["mongodb_client"].close()

    def log_in(self):
        with self.client.session_transaction() as session:
            session["user_id"] = str(self.owner_id)
            session["username"] = "Owner"

    def test_home_page_renders_member_navigation(self):
        self.log_in()

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="members-tab"', response.data)
        self.assertIn(b'id="member-profile"', response.data)

    def test_member_routes_require_login(self):
        self.assertEqual(self.client.get("/api/members").status_code, 401)
        self.assertEqual(self.client.get(f"/api/members/{self.member_id}").status_code, 401)
        self.assertEqual(self.client.get(f"/uploads/{self.cover_name}").status_code, 401)

    def test_member_list_excludes_current_user_and_counts_songs(self):
        self.log_in()

        response = self.client.get("/api/members")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["members"], [
            {"id": str(self.member_id), "username": "Member", "song_count": 1},
        ])
        self.assertNotIn("password_hash", response.get_data(as_text=True))

    def test_member_profile_includes_songs_and_shared_cover_is_accessible(self):
        self.log_in()

        profile = self.client.get(f"/api/members/{self.member_id}")
        cover = self.client.get(f"/uploads/{self.cover_name}")

        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json["username"], "Member")
        self.assertEqual(profile.json["songs"][0]["log"], "A public note")
        self.assertEqual(profile.json["songs"][0]["calificacion"], 4.5)
        self.assertEqual(cover.status_code, 200)
        self.assertEqual(cover.data, b"cover")
        cover.close()

    def test_unknown_member_returns_not_found(self):
        self.log_in()

        self.assertEqual(self.client.get("/api/members/not-an-object-id").status_code, 404)


if __name__ == "__main__":
    unittest.main()
