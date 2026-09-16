"""Session store: signing, expiry, flash data and CSRF tokens."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import time

import pytest

from craft.http.session import (
    CookieSessionStore,
    DatabaseSessionStore,
    FileSessionStore,
    Session,
    sign,
    verify,
)

KEY = "test-application-key"


@pytest.fixture(params=["cookie", "file"])
def store(request, tmp_path):
    if request.param == "cookie":
        return CookieSessionStore(KEY, lifetime=3600)
    return FileSessionStore(KEY, str(tmp_path / "sessions"), lifetime=3600)


class TestSigning:
    def test_signature_is_stable(self):
        assert sign("payload", KEY) == sign("payload", KEY)

    def test_signature_depends_on_the_key(self):
        assert sign("payload", KEY) != sign("payload", "other-key")

    def test_verify_accepts_a_good_signature(self):
        assert verify("payload", sign("payload", KEY), KEY) is True

    def test_verify_rejects_a_bad_signature(self):
        assert verify("payload", "not-the-signature", KEY) is False


class TestRoundTrip:
    def test_values_survive_a_roundtrip(self, store):
        session = store.load(None)
        session.put("user", "jane")
        cookie = store.save(session)

        assert store.load(cookie).get("user") == "jane"

    def test_structured_values_survive(self, store):
        session = store.load(None)
        session.put("cart", {"items": [1, 2, 3]})
        assert store.load(store.save(session)).get("cart") == {"items": [1, 2, 3]}

    def test_missing_key_returns_default(self, store):
        assert store.load(None).get("nope", "fallback") == "fallback"

    def test_tampered_cookie_is_rejected(self, store):
        session = store.load(None)
        session.put("is_admin", False)
        cookie = store.save(session)

        payload, _, signature = cookie.rpartition(".")
        tampered = f"{payload}x.{signature}"

        assert store.load(tampered).get("is_admin") is None

    def test_cookie_signed_with_another_key_is_rejected(self, tmp_path):
        mine = CookieSessionStore(KEY)
        theirs = CookieSessionStore("a-different-key")

        session = theirs.load(None)
        session.put("user", "attacker")

        assert mine.load(theirs.save(session)).get("user") is None

    def test_garbage_cookie_yields_an_empty_session(self, store):
        assert store.load("not-even-close").all() == {}

    def test_expired_session_is_dropped(self, tmp_path):
        store = CookieSessionStore(KEY, lifetime=1)
        session = store.load(None)
        session.put("user", "jane")
        cookie = store.save(session)

        time.sleep(1.1)
        assert store.load(cookie).get("user") is None


class TestSessionApi:
    @pytest.fixture
    def session(self):
        return Session()

    def test_put_and_get(self, session):
        session.put("k", "v")
        assert session.get("k") == "v"

    def test_has_and_exists(self, session):
        session.put("present", "x")
        session.put("empty", None)
        assert session.has("present") is True
        assert session.has("empty") is False
        assert session.exists("empty") is True

    def test_forget(self, session):
        session.put("k", "v")
        session.forget("k")
        assert session.get("k") is None

    def test_pull_reads_then_removes(self, session):
        session.put("k", "v")
        assert session.pull("k") == "v"
        assert session.get("k") is None

    def test_all_hides_internal_keys(self, session):
        session.put("visible", 1)
        session.token()
        assert list(session.all()) == ["visible"]

    def test_flush_keeps_the_csrf_token(self, session):
        token = session.token()
        session.put("k", "v")
        session.flush()
        assert session.get("k") is None
        assert session.token() == token

    def test_invalidate_replaces_the_token_and_id(self, session):
        token, session_id = session.token(), session.id
        session.invalidate()
        assert session.token() != token
        assert session.id != session_id

    def test_regenerate_keeps_data_but_changes_id(self, session):
        session.put("k", "v")
        old_id = session.id
        session.regenerate()
        assert session.id != old_id
        assert session.get("k") == "v"

    def test_dict_style_access(self, session):
        session["k"] = "v"
        assert session["k"] == "v"
        assert "k" in session


class TestCsrfToken:
    def test_token_is_generated_on_first_use(self):
        assert len(Session().token()) > 20

    def test_token_is_stable_within_a_session(self):
        session = Session()
        assert session.token() == session.token()

    def test_token_survives_a_roundtrip(self, store):
        session = store.load(None)
        token = session.token()
        assert store.load(store.save(session)).token() == token

    def test_regenerate_token_changes_it(self):
        session = Session()
        first = session.token()
        assert session.regenerate_token() != first


class TestFlashData:
    def test_flash_is_readable_on_the_next_request(self, store):
        session = store.load(None)
        session.flash("status", "Saved!")
        cookie = store.save(session)

        next_request = store.load(cookie)
        assert next_request.get("status") == "Saved!"

    def test_flash_is_gone_on_the_request_after(self, store):
        session = store.load(None)
        session.flash("status", "Saved!")

        second = store.load(store.save(session))
        third = store.load(store.save(second))

        assert third.get("status") is None

    def test_reflash_keeps_it_one_more_request(self, store):
        session = store.load(None)
        session.flash("status", "Saved!")

        second = store.load(store.save(session))
        second.reflash()
        third = store.load(store.save(second))

        assert third.get("status") == "Saved!"

    def test_normal_values_are_not_aged_out(self, store):
        session = store.load(None)
        session.put("permanent", "here")
        session.flash("temporary", "gone")

        second = store.load(store.save(session))
        third = store.load(store.save(second))

        assert third.get("permanent") == "here"
        assert third.get("temporary") is None


class TestFileStore:
    def test_cookie_carries_only_the_id(self, tmp_path):
        store = FileSessionStore(KEY, str(tmp_path / "sessions"))
        session = store.load(None)
        session.put("secret", "must-not-be-in-the-cookie")
        cookie = store.save(session)

        assert "must-not-be-in-the-cookie" not in cookie

    def test_destroy_invalidates_server_side(self, tmp_path):
        store = FileSessionStore(KEY, str(tmp_path / "sessions"))
        session = store.load(None)
        session.put("user", "jane")
        cookie = store.save(session)

        store.destroy(session.id)
        assert store.load(cookie).get("user") is None

    def test_gc_removes_expired_files(self, tmp_path):
        store = FileSessionStore(KEY, str(tmp_path / "sessions"), lifetime=1)
        session = store.load(None)
        session.put("user", "jane")
        store.save(session)

        time.sleep(1.1)
        assert store.gc() == 1

    def test_a_crafted_id_cannot_escape_the_directory(self, tmp_path):
        directory = tmp_path / "sessions"
        store = FileSessionStore(KEY, str(directory))
        path = store._path("../../etc/passwd")
        assert str(directory) in path
        assert ".." not in path


class TestDatabaseStore:
    def test_cookie_carries_only_the_id(self, migrated_database):
        store = DatabaseSessionStore(KEY, migrated_database)
        session = store.load(None)
        session.put("secret", "must-not-be-in-the-cookie")
        cookie = store.save(session)

        assert "must-not-be-in-the-cookie" not in cookie
        store.destroy(session.id)

    def test_a_round_trip_survives_a_fresh_store_instance(self, migrated_database):
        store = DatabaseSessionStore(KEY, migrated_database)
        session = store.load(None)
        session.put("user", "jane")
        cookie = store.save(session)

        reloaded = DatabaseSessionStore(KEY, migrated_database).load(cookie)
        assert reloaded.get("user") == "jane"
        store.destroy(session.id)

    def test_destroy_invalidates_server_side(self, migrated_database):
        store = DatabaseSessionStore(KEY, migrated_database)
        session = store.load(None)
        session.put("user", "jane")
        cookie = store.save(session)

        store.destroy(session.id)
        assert store.load(cookie).get("user") is None

    def test_revoke_invalidates_without_deleting_the_row(self, migrated_database):
        store = DatabaseSessionStore(KEY, migrated_database)
        session = store.load(None)
        session.put("user", "jane")
        cookie = store.save(session)

        store.revoke(session.id)
        try:
            assert store.load(cookie).get("user") is None, "a revoked session must load empty"
            row = migrated_database.make("db").table("sessions").where("id", session.id).first()
            assert row is not None, "revoke() keeps the row (audit trail), unlike destroy()"
            assert row.get("revoked_at") is not None
        finally:
            store.destroy(session.id)

    def test_revoke_all_for_leaves_the_excepted_session_untouched(self, migrated_database):
        store = DatabaseSessionStore(KEY, migrated_database)
        keep = store.load(None)
        keep.put("user", "jane")
        keep_cookie = store.save(keep)

        others = []
        for _ in range(3):
            other = store.load(None)
            other.put("user", "jane")
            others.append((other.id, store.save(other)))

        try:
            revoked_count = store.revoke_all_for(except_session_id=keep.id)
            assert revoked_count == 3
            assert store.load(keep_cookie).get("user") == "jane", "the excepted session must survive"
            for _, other_cookie in others:
                assert store.load(other_cookie).get("user") is None
        finally:
            store.destroy(keep.id)
            for other_id, _ in others:
                store.destroy(other_id)

    def test_idle_timeout_expires_a_session_independent_of_lifetime(self, migrated_database):
        store = DatabaseSessionStore(KEY, migrated_database, lifetime=3600, idle_timeout=1)
        session = store.load(None)
        session.put("user", "jane")
        cookie = store.save(session)

        time.sleep(1.2)
        try:
            assert store.load(cookie).get("user") is None, "idle timeout must expire it early"
        finally:
            store.destroy(session.id)

    def test_no_idle_timeout_configured_never_expires_early(self, migrated_database):
        store = DatabaseSessionStore(KEY, migrated_database, lifetime=3600, idle_timeout=None)
        session = store.load(None)
        session.put("user", "jane")
        cookie = store.save(session)

        time.sleep(0.1)
        try:
            assert store.load(cookie).get("user") == "jane"
        finally:
            store.destroy(session.id)

    def test_gc_removes_rows_past_their_lifetime(self, migrated_database):
        store = DatabaseSessionStore(KEY, migrated_database, lifetime=1)
        session = store.load(None)
        session.put("user", "jane")
        store.save(session)

        # created_at is second-granularity; 2.1s guarantees strict inequality
        # against the 1s lifetime despite truncation at insert/compare time.
        time.sleep(2.1)
        assert store.gc() >= 1
        assert store.load(store._encode({"id": session.id})).get("user") is None

    def test_make_store_builds_a_database_store_for_the_database_driver(self, migrated_database):
        from craft.http.session import make_store

        config = migrated_database.make("config")
        original_driver = config.get("session.driver")
        original_key = config.get("app.APP_KEY")
        config.set("session.driver", "database")
        config.set("app.APP_KEY", "base64:" + KEY)
        try:
            store = make_store(migrated_database)
            assert isinstance(store, DatabaseSessionStore)
        finally:
            config.set("session.driver", original_driver)
            config.set("app.APP_KEY", original_key)
