from django.contrib.auth import get_user_model
from django.test import TestCase

from .forms import PostForm, RegisterForm
from .models import Post

User = get_user_model()


class RegisterFormUnitTests(TestCase):
    def test_register_form_rejects_password_mismatch(self):
        form = RegisterForm(
            data={
                "first_name": "Jane",
                "last_name": "Doe",
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
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "Jane@Test.Com",
                "password": "VeryStrongPass123!",
                "password_confirm": "VeryStrongPass123!",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["email"], "jane@test.com")


class PostModelUnitTests(TestCase):
    def test_post_author_helpers(self):
        user = User.objects.create_user(
            username="writer@example.com",
            email="writer@example.com",
            first_name="Amina",
            last_name="K",
            password="VeryStrongPass123!",
        )
        post = Post.objects.create(author=user, content="hello")

        self.assertEqual(post.author_handle, "@writer")
        self.assertEqual(post.author_display_name, "Amina K")


class PostFormUnitTests(TestCase):
    def test_post_form_rejects_blank_content(self):
        form = PostForm(data={"content": "   "})
        self.assertFalse(form.is_valid())
        self.assertIn("content", form.errors)

    def test_post_form_trims_content(self):
        form = PostForm(data={"content": "  Test message  "})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["content"], "Test message")
