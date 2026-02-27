from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Post

User = get_user_model()


class AuthFlowTests(TestCase):
    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("accounts:register"),
            data={
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
