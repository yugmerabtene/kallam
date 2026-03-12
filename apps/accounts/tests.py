import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.messaging.encryption import decrypt, encrypt
from apps.messaging.models import Conversation, Message
from apps.posts.models import Post, PostReport

from .models import UserProfile

User = get_user_model()


class AuthFlowTests(TestCase):
    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("accounts:register"),
            data={
                "pseudo": "janedoe",
                "first_name": "Doe",
                "last_name": "Jane",
                "email": "jane@example.com",
                "password": "VeryStrongPass123!",
                "password_confirm": "VeryStrongPass123!",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(email="jane@example.com").exists())
        self.assertContains(response, "Bienvenue")

    def test_login_and_logout(self):
        User.objects.create_user(
            username="john@example.com",
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="VeryStrongPass123!",
        )
        login_response = self.client.post(
            reverse("accounts:login"),
            data={"email": "john@example.com", "password": "VeryStrongPass123!"},
            follow=True,
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertContains(login_response, "Bienvenue")

        logout_response = self.client.post(reverse("accounts:logout"), follow=True)
        self.assertEqual(logout_response.status_code, 200)
        self.assertContains(logout_response, "Connexion")

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(
            username="taken@example.com",
            first_name="A",
            last_name="B",
            email="taken@example.com",
            password="VeryStrongPass123!",
        )
        response = self.client.post(
            reverse("accounts:register"),
            data={
                "pseudo": "cduser",
                "first_name": "C",
                "last_name": "D",
                "email": "taken@example.com",
                "password": "VeryStrongPass123!",
                "password_confirm": "VeryStrongPass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cet email est deja utilise.")

    def test_authenticated_user_can_publish_on_wall(self):
        user = User.objects.create_user(
            username="wall@example.com",
            first_name="Wall",
            last_name="User",
            email="wall@example.com",
            password="VeryStrongPass123!",
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:home"),
            data={"content": "Premier message"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Post.objects.filter(author=user, content="Premier message").exists())
        self.assertContains(response, "Premier message")

    def test_like_and_repost_toggle(self):
        author = User.objects.create_user(
            username="author@example.com",
            first_name="Author",
            last_name="One",
            email="author@example.com",
            password="VeryStrongPass123!",
        )
        actor = User.objects.create_user(
            username="actor@example.com",
            first_name="Actor",
            last_name="Two",
            email="actor@example.com",
            password="VeryStrongPass123!",
        )
        post = Post.objects.create(author=author, content="Action post")
        self.client.force_login(actor)

        like_url = reverse("accounts:post_action", args=[post.id, "like"])
        repost_url = reverse("accounts:post_action", args=[post.id, "repost"])

        first_like = self.client.post(like_url, follow=True)
        self.assertEqual(Post.objects.get(id=post.id).likes.count(), 1)
        second_like = self.client.post(like_url, follow=True)
        self.assertEqual(Post.objects.get(id=post.id).likes.count(), 0)
        first_repost = self.client.post(repost_url, follow=True)
        self.assertEqual(Post.objects.get(id=post.id).reposts.count(), 1)
        second_repost = self.client.post(repost_url, follow=True)
        self.assertEqual(Post.objects.get(id=post.id).reposts.count(), 0)

        self.assertEqual(first_like.status_code, 200)
        self.assertEqual(second_like.status_code, 200)
        self.assertEqual(first_repost.status_code, 200)
        self.assertEqual(second_repost.status_code, 200)
        self.assertContains(second_repost, "Action post")

    def test_report_is_created_once(self):
        author = User.objects.create_user(
            username="author2@example.com",
            first_name="Author",
            last_name="Two",
            email="author2@example.com",
            password="VeryStrongPass123!",
        )
        actor = User.objects.create_user(
            username="actor2@example.com",
            first_name="Actor",
            last_name="Three",
            email="actor2@example.com",
            password="VeryStrongPass123!",
        )
        post = Post.objects.create(author=author, content="Report post")
        self.client.force_login(actor)
        report_url = reverse("accounts:post_action", args=[post.id, "report"])

        response_1 = self.client.post(report_url, follow=True)
        response_2 = self.client.post(report_url, follow=True)

        self.assertEqual(response_1.status_code, 200)
        self.assertEqual(response_2.status_code, 200)
        self.assertContains(response_2, "Publication deja signalee.")
        self.assertEqual(Post.objects.get(id=post.id).reports.count(), 1)

    def test_user_can_publish_image_only(self):
        user = User.objects.create_user(
            username="image@example.com",
            first_name="Img",
            last_name="User",
            email="image@example.com",
            password="VeryStrongPass123!",
        )
        self.client.force_login(user)
        image = SimpleUploadedFile(
            "tiny.gif",
            (
                b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
                b"\xff\xff\xff!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00"
                b"\x00\x00\x01\x00\x01\x00\x00\x02\x02L\x01\x00;"
            ),
            content_type="image/gif",
        )
        with tempfile.TemporaryDirectory() as tmp_media:
            with override_settings(MEDIA_ROOT=tmp_media):
                response = self.client.post(
                    reverse("accounts:home"),
                    data={"content": "", "attachment_url": "", "image": image},
                    follow=True,
                )

        self.assertEqual(response.status_code, 200)
        post = Post.objects.filter(author=user).latest("id")
        self.assertTrue(bool(post.image))
        self.assertContains(response, "/media/posts/images/")

    def test_user_can_publish_youtube_link_and_render_embed(self):
        user = User.objects.create_user(
            username="video@example.com",
            first_name="Video",
            last_name="User",
            email="video@example.com",
            password="VeryStrongPass123!",
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:home"),
            data={
                "content": "Regarde cette video https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        post = Post.objects.filter(author=user).latest("id")
        self.assertEqual(post.youtube_url, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertContains(response, "youtube.com/embed/dQw4w9WgXcQ")

    def test_user_can_publish_file_url_attachment(self):
        user = User.objects.create_user(
            username="file@example.com",
            first_name="File",
            last_name="User",
            email="file@example.com",
            password="VeryStrongPass123!",
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:home"),
            data={
                "content": "",
                "attachment_url": "https://cdn.example.com/docs/guide.pdf",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        post = Post.objects.filter(author=user).latest("id")
        self.assertEqual(post.file_url, "https://cdn.example.com/docs/guide.pdf")
        self.assertContains(response, "Fichier joint")

    def test_rejects_non_file_attachment_url(self):
        user = User.objects.create_user(
            username="badurl@example.com",
            first_name="Bad",
            last_name="Url",
            email="badurl@example.com",
            password="VeryStrongPass123!",
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:home"),
            data={"content": "", "attachment_url": "https://example.com/some-page"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "pointer vers un fichier")


class MessagingTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice@example.com",
            email="alice@example.com",
            first_name="Alice",
            last_name="A",
            password="VeryStrongPass123!",
        )
        self.bob = User.objects.create_user(
            username="bob@example.com",
            email="bob@example.com",
            first_name="Bob",
            last_name="B",
            password="VeryStrongPass123!",
        )
        UserProfile.objects.create(user=self.alice, pseudo="alice")
        UserProfile.objects.create(user=self.bob, pseudo="bob")

    def test_start_conversation_creates_conversation(self):
        self.client.force_login(self.alice)
        response = self.client.post(
            reverse("accounts:start_conversation", args=["bob"]),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Conversation.objects.count(), 1)
        conv = Conversation.objects.first()
        self.assertIn(self.alice, conv.participants.all())
        self.assertIn(self.bob, conv.participants.all())

    def test_start_conversation_reuses_existing(self):
        self.client.force_login(self.alice)
        self.client.post(reverse("accounts:start_conversation", args=["bob"]))
        self.client.post(reverse("accounts:start_conversation", args=["bob"]))
        self.assertEqual(Conversation.objects.count(), 1)

    def test_send_message(self):
        self.client.force_login(self.alice)
        self.client.post(reverse("accounts:start_conversation", args=["bob"]))
        conv = Conversation.objects.first()
        self.client.post(
            reverse("accounts:conversation", args=[conv.pk]),
            data={"content": "Salut Bob !"},
        )
        self.assertEqual(Message.objects.count(), 1)
        msg = Message.objects.first()
        self.assertEqual(msg.sender, self.alice)
        self.assertEqual(msg.content, "Salut Bob !")

    def test_reading_marks_messages_as_read(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.alice, self.bob)
        Message.objects.create(conversation=conv, sender=self.bob, content="Hello !")

        self.client.force_login(self.alice)
        self.client.get(reverse("accounts:conversation", args=[conv.pk]))
        msg = Message.objects.first()
        self.assertIsNotNone(msg.read_at)

    def test_inbox_requires_login(self):
        response = self.client.get(reverse("accounts:inbox"))
        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('accounts:inbox')}",
        )

    def test_cannot_access_other_users_conversation(self):
        charlie = User.objects.create_user(
            username="charlie@example.com",
            email="charlie@example.com",
            password="VeryStrongPass123!",
        )
        conv = Conversation.objects.create()
        conv.participants.add(self.alice, self.bob)
        self.client.force_login(charlie)
        response = self.client.get(reverse("accounts:conversation", args=[conv.pk]))
        self.assertEqual(response.status_code, 404)


class EncryptionTests(TestCase):
    def test_encrypt_decrypt_roundtrip(self):
        plaintext = "Message confidentiel"
        token = encrypt(plaintext)
        self.assertNotEqual(token, plaintext)
        self.assertEqual(decrypt(token), plaintext)

    def test_decrypt_falls_back_on_plain_text(self):
        """Les données non chiffrées (legacy) ne lèvent pas d'exception."""
        result = decrypt("texte non chiffré")
        self.assertEqual(result, "texte non chiffré")

    def test_message_content_is_stored_encrypted(self):
        author = User.objects.create_user(
            username="enc@example.com",
            email="enc@example.com",
            password="VeryStrongPass123!",
        )
        other = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="VeryStrongPass123!",
        )
        conv = Conversation.objects.create()
        conv.participants.add(author, other)
        msg = Message.objects.create(
            conversation=conv, sender=author, content="Secret message"
        )
        self.assertEqual(Message.objects.get(pk=msg.pk).content, "Secret message")
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT content FROM messaging_message WHERE id = %s", [msg.pk])
            raw = cursor.fetchone()[0]
        self.assertNotEqual(raw, "Secret message")
        self.assertTrue(raw.startswith("gAAAAA"))


class ModerationTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff@example.com",
            email="staff@example.com",
            password="VeryStrongPass123!",
            is_staff=True,
        )
        self.regular = User.objects.create_user(
            username="regular@example.com",
            email="regular@example.com",
            password="VeryStrongPass123!",
        )
        self.post = Post.objects.create(author=self.regular, content="Post signalé")
        PostReport.objects.create(post=self.post, reporter=self.staff)

    def test_moderation_dashboard_requires_staff(self):
        self.client.force_login(self.regular)
        response = self.client.get(reverse("accounts:moderation"))
        self.assertEqual(response.status_code, 404)

    def test_moderation_dashboard_accessible_to_staff(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("accounts:moderation"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Post signalé")

    def test_moderation_delete_post(self):
        self.client.force_login(self.staff)
        self.client.post(
            reverse("accounts:moderation_action", args=[self.post.id, "delete"])
        )
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())

    def test_moderation_dismiss_reports(self):
        self.client.force_login(self.staff)
        self.client.post(
            reverse("accounts:moderation_action", args=[self.post.id, "dismiss"])
        )
        self.assertEqual(PostReport.objects.filter(post=self.post).count(), 0)
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())


class PermissionTests(TestCase):
    """Vérifie que les vues protégées redirigent les anonymes vers la page de connexion."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="perm@example.com",
            email="perm@example.com",
            password="VeryStrongPass123!",
        )
        UserProfile.objects.create(user=self.user, pseudo="permuser")
        self.post = Post.objects.create(author=self.user, content="test")

    def _assert_login_required(self, url, method="get"):
        response = getattr(self.client, method)(url)
        login_url = reverse("accounts:login")
        self.assertRedirects(response, f"{login_url}?next={url}")

    def test_home_requires_login(self):
        self._assert_login_required(reverse("accounts:home"))

    def test_edit_profile_requires_login(self):
        self._assert_login_required(reverse("accounts:edit_profile"))

    def test_delete_account_requires_login(self):
        self._assert_login_required(reverse("accounts:delete_account"))

    def test_export_data_requires_login(self):
        self._assert_login_required(reverse("accounts:export_data"))

    def test_inbox_requires_login(self):
        self._assert_login_required(reverse("accounts:inbox"))

    def test_trusted_feed_requires_login(self):
        self._assert_login_required(reverse("accounts:trusted_feed"))

    def test_follow_requires_login(self):
        self._assert_login_required(
            reverse("accounts:follow", args=["permuser"]), method="post"
        )

    def test_post_action_requires_login(self):
        self._assert_login_required(
            reverse("accounts:post_action", args=[self.post.id, "like"]), method="post"
        )
