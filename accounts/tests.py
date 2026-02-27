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
