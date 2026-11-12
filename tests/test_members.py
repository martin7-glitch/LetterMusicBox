import io
import tempfile
import unittest
from pathlib import Path

from bson import ObjectId
from PIL import Image
from werkzeug.security import check_password_hash, generate_password_hash

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

    def create_index(self, *_args, **_kwargs):
        return "username_key"

    def insert_one(self, document):
        inserted_id = ObjectId()
        self.users.append({**document, "_id": inserted_id})
        return type("InsertResult", (), {"inserted_id": inserted_id})()

    @staticmethod
    def project(user, projection):
        if not user or not projection:
            return user
        included_fields = {key for key, included in projection.items() if included}
        return {key: value for key, value in user.items() if key == "_id" or key in included_fields}

    def find(self, _query, projection=None):
        return FakeCursor(self.project(user, projection) for user in self.users)

    def find_one(self, query, projection=None):
        user = next((user for user in self.users if all(user.get(key) == value for key, value in query.items())), None)
        return self.project(user, projection)

    def update_one(self, query, update):
        user = self.find_one(query)
        if not user:
            return type("UpdateResult", (), {"matched_count": 0})()
        user.update(update["$set"])
        return type("UpdateResult", (), {"matched_count": 1})()


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
            {"_id": self.owner_id, "username": "Owner", "password_hash": generate_password_hash("old-password")},
            {"_id": self.member_id, "username": "Member", "password_hash": generate_password_hash("old-password")},
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

    @staticmethod
    def make_png():
        image_buffer = io.BytesIO()
        Image.new("RGB", (2, 2), "blue").save(image_buffer, format="PNG")
        image_buffer.seek(0)
        return image_buffer

    def test_home_page_renders_member_navigation(self):
        self.log_in()

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="members-tab"', response.data)
        self.assertIn(b'id="account-tab"', response.data)
        self.assertIn(b'id="avatar-form"', response.data)
        self.assertIn(b'id="password-form"', response.data)
        self.assertIn(b'id="member-profile"', response.data)

    def test_member_routes_require_login(self):
        self.assertEqual(self.client.get("/api/members").status_code, 401)
        self.assertEqual(self.client.get(f"/api/members/{self.member_id}").status_code, 401)
        self.assertEqual(self.client.get(f"/uploads/{self.cover_name}").status_code, 401)
        self.assertEqual(self.client.post("/api/me/avatar").status_code, 401)
        self.assertEqual(self.client.post("/api/account/password").status_code, 401)
        self.assertEqual(self.client.get("/default-avatars/Default1.jpg").status_code, 401)

    def test_member_list_excludes_current_user_and_counts_songs(self):
        self.log_in()

        response = self.client.get("/api/members")

        self.assertEqual(response.status_code, 200)
        member = response.json["members"][0]
        self.assertEqual(member["id"], str(self.member_id))
        self.assertEqual(member["username"], "Member")
        self.assertEqual(member["song_count"], 1)
        self.assertRegex(member["avatar"], r"^/default-avatars/Default(1[0-9]|20|[1-9])\.jpg$")
        self.assertEqual(
            self.app.extensions["users_collection"].find_one({"_id": self.member_id})["default_avatar"],
            member["avatar"].rsplit("/", 1)[1],
        )
        self.assertNotIn("password_hash", response.get_data(as_text=True))

    def test_default_avatar_is_assigned_and_served_for_signed_in_user(self):
        self.log_in()

        page = self.client.get("/")
        avatar_name = self.app.extensions["users_collection"].find_one(
            {"_id": self.owner_id}
        )["default_avatar"]
        response = self.client.get(f"/default-avatars/{avatar_name}")

        self.assertEqual(page.status_code, 200)
        self.assertIn(f'src="/default-avatars/{avatar_name}"'.encode(), page.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/jpeg")
        response.close()

    def test_registration_assigns_default_avatar_without_asking_for_a_photo(self):
        login_page = self.client.get("/login")
        response = self.client.post(
            "/register",
            data={"username": "NewUser", "password": "new-password"},
        )
        new_user = self.app.extensions["users_collection"].find_one({"username": "NewUser"})

        self.assertNotIn(b'name="avatar"', login_page.data)
        self.assertEqual(response.status_code, 302)
        self.assertIn(new_user["default_avatar"], {
            f"Default{number}.jpg" for number in range(1, 21)
        })

    def test_user_can_upload_avatar_and_members_can_view_it(self):
        with self.client.session_transaction() as session:
            session["user_id"] = str(self.member_id)
            session["username"] = "Member"

        response = self.client.post(
            "/api/me/avatar",
            data={"avatar": (self.make_png(), "avatar.png")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        avatar_url = response.json["avatar"]
        avatar = self.client.get(avatar_url)
        self.assertEqual(avatar.status_code, 200)
        avatar.close()

        self.log_in()
        members = self.client.get("/api/members")
        self.assertEqual(members.json["members"][0]["avatar"], avatar_url)
        profile = self.client.get(f"/api/members/{self.member_id}")
        self.assertEqual(profile.json["avatar"], avatar_url)

    def test_user_can_change_password_with_current_password(self):
        self.log_in()

        wrong_password = self.client.post(
            "/api/account/password",
            data={
                "current_password": "wrong-password",
                "new_password": "new-password",
                "confirm_password": "new-password",
            },
        )
        self.assertEqual(wrong_password.status_code, 400)

        response = self.client.post(
            "/api/account/password",
            data={
                "current_password": "old-password",
                "new_password": "new-password",
                "confirm_password": "new-password",
            },
        )

        self.assertEqual(response.status_code, 200)
        owner = self.app.extensions["users_collection"].find_one({"_id": self.owner_id})
        self.assertTrue(check_password_hash(owner["password_hash"], "new-password"))

    def test_member_profile_includes_songs_and_shared_cover_is_accessible(self):
        self.log_in()

        profile = self.client.get(f"/api/members/{self.member_id}")
        cover = self.client.get(f"/uploads/{self.cover_name}")

        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json["username"], "Member")
        self.assertEqual(profile.json["songs"][0]["imagen"], self.cover_name)
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
