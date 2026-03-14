"""
Tests de l'API REST Django Ninja — couverture complète de apps/accounts/api.py
"""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.messaging.models import Conversation, Message
from apps.moderation.models import ModerationLog
from apps.posts.models import Post, PostReport

from .models import Follow, UserProfile

User = get_user_model()


def _make_user(email, is_staff=False):
    u = User.objects.create_user(
        username=email,
        email=email,
        password="StrongPass123!",
        is_staff=is_staff,
    )
    UserProfile.objects.create(user=u, pseudo=email.split("@")[0])
    return u


class ApiPostsPublicTests(TestCase):
    """GET /api/posts/ et GET /api/posts/{id}/ — accès public."""

    def setUp(self):
        self.author = _make_user("author@api.com")
        self.post = Post.objects.create(author=self.author, content="Hello API")

    def test_list_posts_returns_200(self):
        r = self.client.get("/api/posts/")
        self.assertEqual(r.status_code, 200)

    def test_list_posts_contains_post(self):
        r = self.client.get("/api/posts/")
        data = json.loads(r.content)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["content"], "Hello API")

    def test_list_posts_limit_param(self):
        for i in range(5):
            Post.objects.create(author=self.author, content=f"post {i}")
        r = self.client.get("/api/posts/?limit=3")
        data = json.loads(r.content)
        self.assertLessEqual(len(data), 3)

    def test_get_post_detail_returns_200(self):
        r = self.client.get(f"/api/posts/{self.post.id}/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertEqual(data["id"], self.post.id)

    def test_get_post_detail_404_on_missing(self):
        r = self.client.get("/api/posts/99999/")
        self.assertEqual(r.status_code, 404)


class ApiPostsAuthTests(TestCase):
    """POST /api/posts/ et actions like/repost/report — requiert auth."""

    def setUp(self):
        self.user = _make_user("poster@api.com")
        self.other = _make_user("other@api.com")
        self.post = Post.objects.create(author=self.other, content="Post to act on")

    def test_create_post_authenticated(self):
        self.client.force_login(self.user)
        r = self.client.post(
            "/api/posts/",
            data=json.dumps({"content": "Nouveau post API"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertEqual(data["content"], "Nouveau post API")
        self.assertTrue(Post.objects.filter(content="Nouveau post API").exists())

    def test_create_post_rejects_empty_content(self):
        self.client.force_login(self.user)
        r = self.client.post(
            "/api/posts/",
            data=json.dumps({"content": "   "}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_create_post_requires_auth(self):
        r = self.client.post(
            "/api/posts/",
            data=json.dumps({"content": "non autorisé"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)

    def test_toggle_like_creates_like(self):
        self.client.force_login(self.user)
        r = self.client.post(f"/api/posts/{self.post.id}/like/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertTrue(data["active"])
        self.assertEqual(data["count"], 1)

    def test_toggle_like_removes_like(self):
        self.client.force_login(self.user)
        self.client.post(f"/api/posts/{self.post.id}/like/")
        r = self.client.post(f"/api/posts/{self.post.id}/like/")
        data = json.loads(r.content)
        self.assertFalse(data["active"])
        self.assertEqual(data["count"], 0)

    def test_toggle_repost(self):
        self.client.force_login(self.user)
        r = self.client.post(f"/api/posts/{self.post.id}/repost/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertTrue(data["active"])

    def test_toggle_repost_removes_repost(self):
        self.client.force_login(self.user)
        self.client.post(f"/api/posts/{self.post.id}/repost/")
        r = self.client.post(f"/api/posts/{self.post.id}/repost/")
        data = json.loads(r.content)
        self.assertFalse(data["active"])

    def test_toggle_report(self):
        self.client.force_login(self.user)
        r = self.client.post(f"/api/posts/{self.post.id}/report/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertTrue(data["active"])
        self.assertEqual(PostReport.objects.filter(post=self.post).count(), 1)

    def test_toggle_report_removes_report(self):
        self.client.force_login(self.user)
        self.client.post(f"/api/posts/{self.post.id}/report/")
        r = self.client.post(f"/api/posts/{self.post.id}/report/")
        data = json.loads(r.content)
        self.assertFalse(data["active"])

    def test_like_requires_auth(self):
        r = self.client.post(f"/api/posts/{self.post.id}/like/")
        self.assertEqual(r.status_code, 401)


class ApiProfilesTests(TestCase):
    """GET /api/profiles/{pseudo}/ et /api/profiles/{pseudo}/posts/"""

    def setUp(self):
        self.user = _make_user("profiler@api.com")
        self.post = Post.objects.create(author=self.user, content="Mon post de profil")

    def test_get_profile_returns_200(self):
        r = self.client.get("/api/profiles/profiler/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertEqual(data["pseudo"], "profiler")
        self.assertEqual(data["posts_count"], 1)

    def test_get_profile_404_on_missing(self):
        r = self.client.get("/api/profiles/inexistant/")
        self.assertEqual(r.status_code, 404)

    def test_get_profile_posts(self):
        r = self.client.get("/api/profiles/profiler/posts/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["content"], "Mon post de profil")

    def test_get_profile_posts_empty_for_unknown(self):
        r = self.client.get("/api/profiles/inconnu/posts/")
        self.assertEqual(r.status_code, 404)


class ApiMeTests(TestCase):
    """GET /api/me/ — profil de l'utilisateur connecté."""

    def setUp(self):
        self.user = _make_user("me@api.com")

    def test_get_me_authenticated(self):
        self.client.force_login(self.user)
        r = self.client.get("/api/me/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertEqual(data["pseudo"], "me")

    def test_get_me_requires_auth(self):
        r = self.client.get("/api/me/")
        self.assertEqual(r.status_code, 401)

    def test_get_me_404_without_profile(self):
        user_no_profile = User.objects.create_user(
            username="noprofile@api.com",
            email="noprofile@api.com",
            password="StrongPass123!",
        )
        self.client.force_login(user_no_profile)
        r = self.client.get("/api/me/")
        self.assertEqual(r.status_code, 404)


class ApiFollowTests(TestCase):
    """POST /api/follow/{pseudo}/ — suivre / ne plus suivre."""

    def setUp(self):
        self.alice = _make_user("alice@api.com")
        self.bob = _make_user("bob@api.com")

    def test_follow_user(self):
        self.client.force_login(self.alice)
        r = self.client.post("/api/follow/bob/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertTrue(data["active"])
        self.assertTrue(Follow.objects.filter(follower=self.alice, followed=self.bob).exists())

    def test_unfollow_user(self):
        self.client.force_login(self.alice)
        self.client.post("/api/follow/bob/")
        r = self.client.post("/api/follow/bob/")
        data = json.loads(r.content)
        self.assertFalse(data["active"])
        self.assertFalse(Follow.objects.filter(follower=self.alice, followed=self.bob).exists())

    def test_follow_self_returns_400(self):
        self.client.force_login(self.alice)
        r = self.client.post("/api/follow/alice/")
        self.assertEqual(r.status_code, 400)

    def test_follow_requires_auth(self):
        r = self.client.post("/api/follow/bob/")
        self.assertEqual(r.status_code, 401)


class ApiMessagingTests(TestCase):
    """Conversations et messages via l'API."""

    def setUp(self):
        self.alice = _make_user("alice2@api.com")
        self.bob = _make_user("bob2@api.com")
        self.charlie = _make_user("charlie@api.com")

    def test_list_conversations_empty(self):
        self.client.force_login(self.alice)
        r = self.client.get("/api/conversations/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(json.loads(r.content), [])

    def test_start_conversation(self):
        self.client.force_login(self.alice)
        r = self.client.post("/api/conversations/?pseudo=bob2")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertEqual(data["other_pseudo"], "bob2")
        self.assertEqual(Conversation.objects.count(), 1)

    def test_start_conversation_reuses_existing(self):
        self.client.force_login(self.alice)
        self.client.post("/api/conversations/?pseudo=bob2")
        r = self.client.post("/api/conversations/?pseudo=bob2")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Conversation.objects.count(), 1)

    def test_start_conversation_self_returns_400(self):
        self.client.force_login(self.alice)
        r = self.client.post("/api/conversations/?pseudo=alice2")
        self.assertEqual(r.status_code, 400)

    def test_list_conversations_shows_created(self):
        self.client.force_login(self.alice)
        self.client.post("/api/conversations/?pseudo=bob2")
        r = self.client.get("/api/conversations/")
        data = json.loads(r.content)
        self.assertEqual(len(data), 1)

    def test_send_and_list_messages(self):
        self.client.force_login(self.alice)
        self.client.post("/api/conversations/?pseudo=bob2")
        conv = Conversation.objects.first()

        r = self.client.post(
            f"/api/conversations/{conv.id}/messages/",
            data=json.dumps({"content": "Salut depuis l'API !"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Message.objects.count(), 1)

        r2 = self.client.get(f"/api/conversations/{conv.id}/messages/")
        msgs = json.loads(r2.content)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["content"], "Salut depuis l'API !")

    def test_send_message_empty_content_returns_400(self):
        self.client.force_login(self.alice)
        self.client.post("/api/conversations/?pseudo=bob2")
        conv = Conversation.objects.first()
        r = self.client.post(
            f"/api/conversations/{conv.id}/messages/",
            data=json.dumps({"content": "   "}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_list_messages_forbidden_for_non_participant(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.alice, self.bob)
        self.client.force_login(self.charlie)
        r = self.client.get(f"/api/conversations/{conv.id}/messages/")
        self.assertEqual(r.status_code, 403)

    def test_send_message_forbidden_for_non_participant(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.alice, self.bob)
        self.client.force_login(self.charlie)
        r = self.client.post(
            f"/api/conversations/{conv.id}/messages/",
            data=json.dumps({"content": "intrusion"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)

    def test_conversations_requires_auth(self):
        r = self.client.get("/api/conversations/")
        self.assertEqual(r.status_code, 401)


class ApiModerationTests(TestCase):
    """Endpoints de modération — réservés au staff."""

    def setUp(self):
        self.staff = _make_user("staffapi@api.com", is_staff=True)
        self.regular = _make_user("regular@api.com")
        self.post = Post.objects.create(author=self.regular, content="Post signalé API")
        PostReport.objects.create(post=self.post, reporter=self.staff)

    def test_list_reported_posts_as_staff(self):
        self.client.force_login(self.staff)
        r = self.client.get("/api/moderation/reports/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["content"], "Post signalé API")

    def test_list_reported_posts_forbidden_for_regular(self):
        self.client.force_login(self.regular)
        r = self.client.get("/api/moderation/reports/")
        self.assertEqual(r.status_code, 403)

    def test_list_reported_posts_requires_auth(self):
        r = self.client.get("/api/moderation/reports/")
        self.assertEqual(r.status_code, 401)

    def test_moderate_delete_post(self):
        self.client.force_login(self.staff)
        r = self.client.post(f"/api/moderation/{self.post.id}/delete/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertTrue(data["success"])
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())
        self.assertTrue(ModerationLog.objects.filter(action=ModerationLog.ACTION_DELETE).exists())

    def test_moderate_delete_forbidden_for_regular(self):
        self.client.force_login(self.regular)
        r = self.client.post(f"/api/moderation/{self.post.id}/delete/")
        self.assertEqual(r.status_code, 403)

    def test_moderate_dismiss_reports(self):
        self.client.force_login(self.staff)
        r = self.client.post(f"/api/moderation/{self.post.id}/dismiss/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertTrue(data["success"])
        self.assertEqual(PostReport.objects.filter(post=self.post).count(), 0)
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())
        self.assertTrue(ModerationLog.objects.filter(action=ModerationLog.ACTION_DISMISS).exists())

    def test_moderate_dismiss_forbidden_for_regular(self):
        self.client.force_login(self.regular)
        r = self.client.post(f"/api/moderation/{self.post.id}/dismiss/")
        self.assertEqual(r.status_code, 403)

    def test_list_moderation_log_as_staff(self):
        self.client.force_login(self.staff)
        ModerationLog.objects.create(
            actor=self.staff,
            action=ModerationLog.ACTION_DELETE,
            post_id_ref=self.post.id,
            post_preview="préview",
        )
        r = self.client.get("/api/moderation/log/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertGreaterEqual(len(data), 1)

    def test_list_moderation_log_forbidden_for_regular(self):
        self.client.force_login(self.regular)
        r = self.client.get("/api/moderation/log/")
        self.assertEqual(r.status_code, 403)
