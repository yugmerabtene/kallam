from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.messaging.encryption import decrypt, encrypt
from apps.messaging.models import Conversation, Message
from apps.posts.forms import PostForm
from apps.posts.models import Post, extract_first_youtube_url, extract_youtube_video_id, is_file_url

from .forms import RegisterForm

User = get_user_model()


class RegisterFormUnitTests(TestCase):
    def test_register_form_rejects_password_mismatch(self):
        form = RegisterForm(
            data={
                "pseudo": "janedoe",
                "email": "jane@test.com",
                "password": "VeryStrongPass123!",
                "password_confirm": "DifferentPass123!",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("password_confirm", form.errors)

    def test_register_form_normalizes_email(self):
        form = RegisterForm(
            data={
                "pseudo": "janedoe",
                "email": "Jane@Test.Com",
                "password": "VeryStrongPass123!",
                "password_confirm": "VeryStrongPass123!",
                "cgu_accepted": True,
            }
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["email"], "jane@test.com")


class PostModelUnitTests(TestCase):
    def test_post_author_helpers(self):
        user = User.objects.create_user(
            username="writer@example.com",
            email="writer@example.com",
            password="VeryStrongPass123!",
        )
        post = Post.objects.create(author=user, content="hello")

        self.assertEqual(post.author_handle, "@writer")
        self.assertEqual(post.author_display_name, "@writer")

    def test_extract_youtube_video_id(self):
        self.assertEqual(
            extract_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )
        self.assertEqual(
            extract_youtube_video_id("https://youtu.be/dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )
        self.assertEqual(
            extract_youtube_video_id("https://youtube.com/shorts/dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )
        self.assertEqual(
            extract_youtube_video_id("https://example.com/video?id=dQw4w9WgXcQ"),
            "",
        )

    def test_extract_first_youtube_url_from_text(self):
        content = "Hello regarde ça https://youtu.be/dQw4w9WgXcQ merci"
        self.assertEqual(
            extract_first_youtube_url(content),
            "https://youtu.be/dQw4w9WgXcQ",
        )

    def test_is_file_url(self):
        self.assertTrue(is_file_url("https://cdn.example.com/docs/guide.pdf"))
        self.assertTrue(is_file_url("https://cdn.example.com/videos/demo.mp4"))
        self.assertFalse(is_file_url("https://example.com/page"))
        self.assertFalse(is_file_url("https://example.com/watch?v=abc"))


class PostFormUnitTests(TestCase):
    def test_post_form_rejects_blank_content(self):
        form = PostForm(data={"content": "   "})
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_post_form_trims_content(self):
        form = PostForm(data={"content": "  Test message  "})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["content"], "Test message")

    def test_post_form_accepts_youtube_in_message_text(self):
        form = PostForm(data={"content": "video https://youtu.be/dQw4w9WgXcQ"})
        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data["youtube_url"],
            "https://youtu.be/dQw4w9WgXcQ",
        )

    def test_post_form_rejects_non_file_attachment_url(self):
        form = PostForm(data={"content": "", "attachment_url": "https://example.com/nope"})
        self.assertFalse(form.is_valid())
        self.assertIn("attachment_url", form.errors)


class EncryptionUnitTests(TestCase):
    def test_roundtrip(self):
        self.assertEqual(decrypt(encrypt("hello")), "hello")

    def test_empty_string(self):
        self.assertEqual(encrypt(""), "")
        self.assertEqual(decrypt(""), "")

    def test_none(self):
        self.assertIsNone(encrypt(None))
        self.assertIsNone(decrypt(None))


class RetentionCommandTests(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user(
            username="u1@ex.com", email="u1@ex.com", password="pass"
        )
        self.u2 = User.objects.create_user(
            username="u2@ex.com", email="u2@ex.com", password="pass"
        )

    def _make_conv_with_message(self, days_ago):
        conv = Conversation.objects.create()
        conv.participants.add(self.u1, self.u2)
        msg = Message.objects.create(
            conversation=conv, sender=self.u1, content="test"
        )
        Message.objects.filter(pk=msg.pk).update(
            created_at=timezone.now() - timedelta(days=days_ago)
        )
        return conv, msg

    def test_dry_run_does_not_delete(self):
        self._make_conv_with_message(days_ago=120)
        call_command("clean_old_messages", days=90, dry_run=True)
        self.assertEqual(Message.objects.count(), 1)

    def test_deletes_old_messages(self):
        self._make_conv_with_message(days_ago=120)
        call_command("clean_old_messages", days=90)
        self.assertEqual(Message.objects.count(), 0)

    def test_keeps_recent_messages(self):
        self._make_conv_with_message(days_ago=10)
        call_command("clean_old_messages", days=90)
        self.assertEqual(Message.objects.count(), 1)
