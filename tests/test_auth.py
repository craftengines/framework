"""Password hashing, authentication and the authorization gate."""

import pytest

from services.auth.gate import GateManager
from services.auth.manager import AuthManager
from services.auth.password import Hash
from services.exceptions.handler import AuthorizationException


class TestHash:
    def test_hash_is_not_the_plaintext(self):
        assert Hash.make("secret") != "secret"

    def test_check_accepts_the_right_password(self):
        assert Hash.check("secret", Hash.make("secret")) is True

    def test_check_rejects_the_wrong_password(self):
        assert Hash.check("wrong", Hash.make("secret")) is False

    def test_hashes_are_salted_and_therefore_unique(self):
        assert Hash.make("secret") != Hash.make("secret")

    def test_check_against_none_is_false(self):
        assert Hash.check("secret", None) is False

    def test_check_against_plaintext_is_false(self):
        # A stored plaintext value must never authenticate.
        assert Hash.check("secret", "secret") is False

    def test_is_hashed_detects_framework_hashes(self):
        assert Hash.is_hashed(Hash.make("secret")) is True
        assert Hash.is_hashed("plaintext") is False
        assert Hash.is_hashed(None) is False

    def test_is_hashed_recognises_bcrypt_prefixes(self):
        assert Hash.is_hashed("$2b$12$abcdefghijklmnopqrstuv") is True


class TestAuthManager:
    @pytest.fixture
    def auth(self, migrated_database):
        manager = AuthManager(migrated_database)
        manager.logout()
        return manager

    @pytest.fixture
    def user(self):
        from app.Models.User import User

        from codepy.facades import DB

        DB.statement("DELETE FROM users WHERE email = 'auth-test@codepy.local'")
        return User.create(
            {
                "name": "Auth Test",
                "email": "auth-test@codepy.local",
                "password": "correct-horse",
                "is_admin": False,
            }
        )

    def test_starts_as_a_guest(self, auth):
        assert auth.check() is False
        assert auth.guest() is True
        assert auth.user() is None

    def test_password_is_stored_hashed(self, user):
        assert user.get_attribute("password") != "correct-horse"
        assert Hash.is_hashed(user.get_attribute("password"))

    def test_attempt_succeeds_with_valid_credentials(self, auth, user):
        assert auth.attempt(
            {"email": "auth-test@codepy.local", "password": "correct-horse"}
        ) is True
        assert auth.check() is True
        assert auth.user().get_attribute("email") == "auth-test@codepy.local"

    def test_attempt_fails_with_a_wrong_password(self, auth, user):
        assert auth.attempt(
            {"email": "auth-test@codepy.local", "password": "nope"}
        ) is False
        assert auth.guest() is True

    def test_attempt_fails_for_an_unknown_user(self, auth, user):
        assert auth.attempt({"email": "ghost@codepy.local", "password": "x"}) is False

    def test_attempt_without_a_password_fails(self, auth, user):
        assert auth.attempt({"email": "auth-test@codepy.local"}) is False

    def test_logout_clears_the_user(self, auth, user):
        auth.attempt({"email": "auth-test@codepy.local", "password": "correct-horse"})
        auth.logout()
        assert auth.check() is False

    def test_login_using_id(self, auth, user):
        assert auth.login_using_id(user.get_attribute("id")) is not None
        assert auth.check() is True

    def test_once_authenticates_without_persisting(self, auth, user):
        assert auth.once(
            {"email": "auth-test@codepy.local", "password": "correct-horse"}
        ) is True
        assert auth.guest() is True

    def test_check_password_on_the_model(self, user):
        assert user.check_password("correct-horse") is True
        assert user.check_password("wrong") is False

    def test_password_is_hidden_from_serialization(self, user):
        assert "password" not in user.to_dict()


class TestGate:
    @pytest.fixture
    def gate(self):
        return GateManager()

    def test_unknown_ability_is_denied_by_default(self, gate):
        assert gate.allows("anything", object()) is False

    def test_defined_ability_is_consulted(self, gate):
        gate.define("edit", lambda user: user == "owner")
        assert gate.allows("edit", "owner") is True
        assert gate.allows("edit", "stranger") is False

    def test_denies_is_the_inverse(self, gate):
        gate.define("edit", lambda user: True)
        assert gate.denies("edit", "anyone") is False

    def test_policy_is_used_for_the_model(self, gate):
        class Post:
            pass

        class PostPolicy:
            def update(self, user, post):
                return user == "author"

        gate.policy(Post, PostPolicy)
        assert gate.allows("update", "author", Post()) is True
        assert gate.allows("update", "reader", Post()) is False

    def test_authorize_raises_when_denied(self, gate):
        with pytest.raises(AuthorizationException):
            gate.authorize("missing", object())

    def test_authorize_is_silent_when_allowed(self, gate):
        gate.define("view", lambda user: True)
        gate.authorize("view", object())
