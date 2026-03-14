"""
Tests des vues HTML non couvertes — vues profil, post_detail, édition profil,
follow/trust, suppression compte, export, journal modération, CGU, enquête,
fil de confiance.
"""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.governance.models import TrustList
from apps.messaging.models import Conversation, Message
from apps.moderation.models import ModerationLog
from apps.posts.models import Post, PostReport

from .models import Follow, UserProfile

User = get_user_model()


def _create_user(email, is_staff=False, pseudo=None):
    u = User.objects.create_user(
        username=email,
        email=email,
        password="StrongPass123!",
        is_staff=is_staff,
    )
    if pseudo is None:
        pseudo = email.split("@")[0]
    UserProfile.objects.create(user=u, pseudo=pseudo)
    return u


class ProfileViewTests(TestCase):
    """GET /profil/{pseudo}/ — vue publique et authentifiée."""

    def setUp(self):
        self.user = _create_user("profview@test.com", pseudo="profview")
        self.visitor = _create_user("visitor@test.com", pseudo="visitor")
        self.post = Post.objects.create(author=self.user, content="Post sur profil")

    def test_profile_view_anonymous(self):
        r = self.client.get(reverse("accounts:profile", args=["profview"]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "profview")

    def test_profile_view_authenticated(self):
        self.client.force_login(self.visitor)
        r = self.client.get(reverse("accounts:profile", args=["profview"]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Post sur profil")

    def test_profile_view_own_profile(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("accounts:profile", args=["profview"]))
        self.assertEqual(r.status_code, 200)

    def test_profile_view_404_on_unknown(self):
        r = self.client.get(reverse("accounts:profile", args=["inexistant"]))
        self.assertEqual(r.status_code, 404)

    def test_profile_view_shows_followers_count(self):
        Follow.objects.create(follower=self.visitor, followed=self.user)
        r = self.client.get(reverse("accounts:profile", args=["profview"]))
        self.assertContains(r, "1")


class PostDetailViewTests(TestCase):
    """GET /posts/{id}/ — détail d'une publication."""

    def setUp(self):
        self.author = _create_user("postdetail@test.com", pseudo="postdetail")
        self.post = Post.objects.create(author=self.author, content="Détail du post")

    def test_post_detail_anonymous(self):
        r = self.client.get(reverse("accounts:post_detail", args=[self.post.id]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Détail du post")

    def test_post_detail_authenticated(self):
        self.client.force_login(self.author)
        r = self.client.get(reverse("accounts:post_detail", args=[self.post.id]))
        self.assertEqual(r.status_code, 200)

    def test_post_detail_404_on_missing(self):
        r = self.client.get(reverse("accounts:post_detail", args=[99999]))
        self.assertEqual(r.status_code, 404)


class EditProfileViewTests(TestCase):
    """GET + POST /profil/modifier/"""

    def setUp(self):
        self.user = _create_user("editpro@test.com", pseudo="editpro")

    def test_get_edit_profile_form(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("accounts:edit_profile"))
        self.assertEqual(r.status_code, 200)

    def test_post_edit_profile_updates_bio(self):
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("accounts:edit_profile"),
            data={"pseudo": "editpro", "bio": "Ma nouvelle bio", "langue": "fr"},
            follow=True,
        )
        self.assertEqual(r.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.bio, "Ma nouvelle bio")


class FollowViewTests(TestCase):
    """POST /profil/{pseudo}/suivre/ — logique follow/unfollow."""

    def setUp(self):
        self.alice = _create_user("alice@follow.com", pseudo="alice")
        self.bob = _create_user("bob@follow.com", pseudo="bob")

    def test_follow_creates_relation(self):
        self.client.force_login(self.alice)
        self.client.post(reverse("accounts:follow", args=["bob"]))
        self.assertTrue(Follow.objects.filter(follower=self.alice, followed=self.bob).exists())

    def test_follow_twice_removes_relation(self):
        self.client.force_login(self.alice)
        self.client.post(reverse("accounts:follow", args=["bob"]))
        self.client.post(reverse("accounts:follow", args=["bob"]))
        self.assertFalse(Follow.objects.filter(follower=self.alice, followed=self.bob).exists())

    def test_follow_self_does_not_create_relation(self):
        self.client.force_login(self.alice)
        self.client.post(reverse("accounts:follow", args=["alice"]))
        self.assertFalse(Follow.objects.filter(follower=self.alice, followed=self.alice).exists())

    def test_follow_redirects_to_profile(self):
        self.client.force_login(self.alice)
        r = self.client.post(reverse("accounts:follow", args=["bob"]))
        self.assertRedirects(r, reverse("accounts:profile", args=["bob"]))


class DeleteAccountViewTests(TestCase):
    """GET + POST /supprimer-mon-compte/"""

    def setUp(self):
        self.user = _create_user("del@test.com", pseudo="deluser")

    def test_get_delete_account_form(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("accounts:delete_account"))
        self.assertEqual(r.status_code, 200)

    def test_delete_with_wrong_password_keeps_account(self):
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("accounts:delete_account"),
            data={"password": "WrongPassword!"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(User.objects.filter(email="del@test.com").exists())

    def test_delete_with_correct_password_removes_account(self):
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("accounts:delete_account"),
            data={"password": "StrongPass123!"},
            follow=True,
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(email="del@test.com").exists())


class ExportDataViewTests(TestCase):
    """GET /mes-donnees/ — export JSON RGPD."""

    def setUp(self):
        self.user = _create_user("export@test.com", pseudo="exportuser")
        Post.objects.create(author=self.user, content="Post à exporter")

    def test_export_returns_json(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("accounts:export_data"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/json; charset=utf-8")

    def test_export_contains_user_data(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("accounts:export_data"))
        data = json.loads(r.content)
        self.assertEqual(data["user"]["email"], "export@test.com")
        self.assertNotIn("first_name", data["user"])
        self.assertNotIn("last_name", data["user"])
        self.assertEqual(data["profile"]["pseudo"], "exportuser")
        self.assertEqual(len(data["posts"]), 1)
        self.assertEqual(data["posts"][0]["content"], "Post à exporter")

    def test_export_attachment_filename(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("accounts:export_data"))
        self.assertIn("attachment", r["Content-Disposition"])


class ModerationLogViewTests(TestCase):
    """GET /moderation/journal/ — journal de modération (staff)."""

    def setUp(self):
        self.staff = _create_user("stafflog@test.com", is_staff=True, pseudo="stafflog")
        self.regular = _create_user("reglog@test.com", pseudo="reglog")

    def test_log_accessible_to_staff(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse("accounts:moderation_log"))
        self.assertEqual(r.status_code, 200)

    def test_log_requires_staff(self):
        self.client.force_login(self.regular)
        r = self.client.get(reverse("accounts:moderation_log"))
        self.assertEqual(r.status_code, 404)

    def test_log_requires_auth(self):
        r = self.client.get(reverse("accounts:moderation_log"))
        self.assertEqual(r.status_code, 404)

    def test_log_shows_entries(self):
        post = Post.objects.create(author=self.regular, content="logged post")
        ModerationLog.objects.create(
            actor=self.staff,
            action=ModerationLog.ACTION_DELETE,
            post_id_ref=post.id,
            post_preview="logged post",
        )
        self.client.force_login(self.staff)
        r = self.client.get(reverse("accounts:moderation_log"))
        self.assertContains(r, "logged post")


class CguViewTests(TestCase):
    """GET /cgu/ — page publique des conditions d'utilisation."""

    def test_cgu_returns_200_anonymous(self):
        r = self.client.get(reverse("accounts:cgu"))
        self.assertEqual(r.status_code, 200)

    def test_cgu_returns_200_authenticated(self):
        user = _create_user("cguser@test.com", pseudo="cguser")
        self.client.force_login(user)
        r = self.client.get(reverse("accounts:cgu"))
        self.assertEqual(r.status_code, 200)


class TrustViewTests(TestCase):
    """POST /profil/{pseudo}/confiance/ — ajouter/retirer la confiance."""

    def setUp(self):
        self.alice = _create_user("alice@trust.com", pseudo="alicetrust")
        self.bob = _create_user("bob@trust.com", pseudo="bobtrust")

    def test_trust_creates_relation(self):
        self.client.force_login(self.alice)
        self.client.post(reverse("accounts:trust", args=["bobtrust"]))
        self.assertTrue(TrustList.objects.filter(user=self.alice, trusted=self.bob).exists())

    def test_trust_twice_removes_relation(self):
        self.client.force_login(self.alice)
        self.client.post(reverse("accounts:trust", args=["bobtrust"]))
        self.client.post(reverse("accounts:trust", args=["bobtrust"]))
        self.assertFalse(TrustList.objects.filter(user=self.alice, trusted=self.bob).exists())

    def test_trust_self_does_not_create_relation(self):
        self.client.force_login(self.alice)
        self.client.post(reverse("accounts:trust", args=["alicetrust"]))
        self.assertFalse(TrustList.objects.filter(user=self.alice, trusted=self.alice).exists())

    def test_trust_requires_login(self):
        r = self.client.post(reverse("accounts:trust", args=["bobtrust"]))
        self.assertRedirects(
            r,
            f"{reverse('accounts:login')}?next={reverse('accounts:trust', args=['bobtrust'])}",
        )


class TrustedFeedViewTests(TestCase):
    """GET /fil-confiance/ — fil filtré par liste de confiance."""

    def setUp(self):
        self.alice = _create_user("alice@feed.com", pseudo="alicefeed")
        self.bob = _create_user("bob@feed.com", pseudo="bobfeed")
        self.post = Post.objects.create(author=self.bob, content="Post de confiance")

    def test_trusted_feed_empty_without_trusted(self):
        self.client.force_login(self.alice)
        r = self.client.get(reverse("accounts:trusted_feed"))
        self.assertEqual(r.status_code, 200)

    def test_trusted_feed_shows_trusted_posts(self):
        TrustList.objects.create(user=self.alice, trusted=self.bob)
        self.client.force_login(self.alice)
        r = self.client.get(reverse("accounts:trusted_feed"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Post de confiance")

    def test_trusted_feed_hides_untrusted_posts(self):
        self.client.force_login(self.alice)
        r = self.client.get(reverse("accounts:trusted_feed"))
        self.assertNotContains(r, "Post de confiance")


class SurveyViewTests(TestCase):
    """GET + POST /enquete/ — questionnaire anonyme."""

    def test_survey_get_returns_200(self):
        r = self.client.get(reverse("accounts:survey"))
        self.assertEqual(r.status_code, 200)

    def test_survey_get_creates_question_if_none(self):
        from apps.governance.models import SurveyQuestion
        self.assertEqual(SurveyQuestion.objects.count(), 0)
        self.client.get(reverse("accounts:survey"))
        self.assertEqual(SurveyQuestion.objects.count(), 1)

    def test_survey_post_creates_response(self):
        from apps.governance.models import SurveyResponse
        r = self.client.post(
            reverse("accounts:survey"),
            data={"answer": "Je veux plus de confidentialité"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(SurveyResponse.objects.count(), 1)

    def test_survey_post_rejects_empty_answer(self):
        from apps.governance.models import SurveyResponse
        r = self.client.post(reverse("accounts:survey"), data={"answer": ""})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(SurveyResponse.objects.count(), 0)

    def test_survey_post_rejects_too_long_answer(self):
        from apps.governance.models import SurveyResponse
        long_answer = "x" * 1001
        r = self.client.post(reverse("accounts:survey"), data={"answer": long_answer})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(SurveyResponse.objects.count(), 0)


class LoginRateLimitTests(TestCase):
    """Branche rate limit du login view (5 tentatives / 5 min)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="ratelimit@test.com",
            email="ratelimit@test.com",
            password="StrongPass123!",
        )

    def tearDown(self):
        from django.core.cache import cache
        cache.delete("login:127.0.0.1")

    def test_login_blocked_after_5_failed_attempts(self):
        from django.core.cache import cache
        # Injecter directement le compteur au-dessus du seuil
        cache.set("login:127.0.0.1", 5, timeout=300)
        r = self.client.post(
            reverse("accounts:login"),
            data={"email": "ratelimit@test.com", "password": "StrongPass123!"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Trop de tentatives")

    def test_login_invalid_credentials_shows_error(self):
        r = self.client.post(
            reverse("accounts:login"),
            data={"email": "ratelimit@test.com", "password": "WrongPassword!"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Identifiants invalides")


class PostActionInvalidTests(TestCase):
    """Branche 'else' de post_action_view — action inconnue."""

    def setUp(self):
        self.user = _create_user("action@test.com", pseudo="actionuser")
        self.post = Post.objects.create(author=self.user, content="Action test")

    def test_invalid_action_shows_error(self):
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("accounts:post_action", args=[self.post.id, "invalide"]),
            follow=True,
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Action non supportee")


# ---------------------------------------------------------------------------
# Integration & non-regression tests
# ---------------------------------------------------------------------------


class MentionsLegalesIntegrationTests(TestCase):
    """GET /mentions-legales/ — page légale accessible à tous."""

    def test_mentions_legales_anonymous_returns_200(self):
        r = self.client.get(reverse("accounts:mentions_legales"))
        self.assertEqual(r.status_code, 200)

    def test_mentions_legales_authenticated_returns_200(self):
        user = _create_user("legal@test.com", pseudo="legaluser")
        self.client.force_login(user)
        r = self.client.get(reverse("accounts:mentions_legales"))
        self.assertEqual(r.status_code, 200)

    def test_mentions_legales_contains_legal_content(self):
        r = self.client.get(reverse("accounts:mentions_legales"))
        # Vérifie que la page contient du contenu juridique attendu
        self.assertContains(r, "INEAD")


class I18nLanguageSwitchTests(TestCase):
    """Commutation de langue via /i18n/setlang/ + cookie LANGUAGE_COOKIE_NAME."""

    SET_LANG_URL = "/i18n/setlang/"

    def _switch_language(self, lang_code):
        return self.client.post(
            self.SET_LANG_URL,
            data={"language": lang_code, "next": "/"},
            follow=True,
        )

    def test_switch_to_english(self):
        r = self._switch_language("en")
        self.assertEqual(r.status_code, 200)

    def test_switch_to_arabic(self):
        r = self._switch_language("ar")
        self.assertEqual(r.status_code, 200)

    def test_switch_to_german(self):
        r = self._switch_language("de")
        self.assertEqual(r.status_code, 200)

    def test_switch_to_spanish(self):
        r = self._switch_language("es")
        self.assertEqual(r.status_code, 200)

    def test_switch_to_italian(self):
        r = self._switch_language("it")
        self.assertEqual(r.status_code, 200)

    def test_switch_to_french(self):
        r = self._switch_language("fr")
        self.assertEqual(r.status_code, 200)

    def test_english_login_page_translated(self):
        """La page de connexion en anglais affiche 'Log in', pas 'Se connecter'."""
        self.client.post(self.SET_LANG_URL, data={"language": "en", "next": "/"})
        r = self.client.get(reverse("accounts:login"))
        self.assertContains(r, "Log in")

    def test_german_login_page_translated(self):
        """La page de connexion en allemand affiche 'Anmelden'."""
        self.client.post(self.SET_LANG_URL, data={"language": "de", "next": "/"})
        r = self.client.get(reverse("accounts:login"))
        self.assertContains(r, "Anmelden")

    def test_spanish_login_page_translated(self):
        """La page de connexion en espagnol affiche 'Iniciar sesión'."""
        self.client.post(self.SET_LANG_URL, data={"language": "es", "next": "/"})
        r = self.client.get(reverse("accounts:login"))
        self.assertContains(r, "Iniciar")

    def test_italian_login_page_translated(self):
        """La page de connexion en italien affiche 'Accedi'."""
        self.client.post(self.SET_LANG_URL, data={"language": "it", "next": "/"})
        r = self.client.get(reverse("accounts:login"))
        self.assertContains(r, "Accedi")


class PseudonymRegistrationTests(TestCase):
    """Non-régression pseudonymat — aucun nom civil dans l'inscription."""

    REGISTER_URL_NAME = "accounts:register"

    def test_register_form_does_not_expose_first_name_field(self):
        """Le formulaire d'inscription ne doit pas contenir de champ prénom."""
        r = self.client.get(reverse(self.REGISTER_URL_NAME))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'name="first_name"')
        self.assertNotContains(r, 'name="last_name"')

    def test_register_succeeds_with_pseudo_email_password_only(self):
        """L'inscription ne nécessite que pseudo, email et mot de passe."""
        r = self.client.post(
            reverse(self.REGISTER_URL_NAME),
            data={
                "pseudo": "testpseudo",
                "email": "pseudo@test.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "cgu_accepted": True,
            },
            follow=True,
        )
        self.assertEqual(r.status_code, 200)
        user = User.objects.filter(email="pseudo@test.com").first()
        self.assertIsNotNone(user)

    def test_registered_user_has_no_first_or_last_name(self):
        """Un utilisateur inscrit n'a ni prénom ni nom enregistrés."""
        self.client.post(
            reverse(self.REGISTER_URL_NAME),
            data={
                "pseudo": "anonuser",
                "email": "anon@test.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "cgu_accepted": True,
            },
        )
        user = User.objects.filter(email="anon@test.com").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.first_name, "")
        self.assertEqual(user.last_name, "")

    def test_profile_page_does_not_show_civil_name(self):
        """La page profil n'affiche pas de prénom/nom civil."""
        user = _create_user("civilname@test.com", pseudo="civiltest")
        user.first_name = "Jean"
        user.last_name = "Dupont"
        user.save()
        r = self.client.get(reverse("accounts:profile", args=["civiltest"]))
        self.assertNotContains(r, "Jean")
        self.assertNotContains(r, "Dupont")


class ExportDataPrivacyTests(TestCase):
    """Non-régression RGPD — l'export ne fuit pas les données civiles."""

    def setUp(self):
        self.user = _create_user("exporttest@test.com", pseudo="exportuser")
        self.user.first_name = "Marie"
        self.user.last_name = "Curie"
        self.user.save()
        self.client.force_login(self.user)

    def test_export_returns_200(self):
        r = self.client.get(reverse("accounts:export_data"))
        self.assertEqual(r.status_code, 200)

    def test_export_is_json(self):
        r = self.client.get(reverse("accounts:export_data"))
        self.assertIn("application/json", r["Content-Type"])

    def test_export_contains_email(self):
        r = self.client.get(reverse("accounts:export_data"))
        data = json.loads(r.content)
        self.assertEqual(data["user"]["email"], "exporttest@test.com")

    def test_export_does_not_contain_first_name(self):
        r = self.client.get(reverse("accounts:export_data"))
        content = r.content.decode()
        self.assertNotIn("first_name", content)
        self.assertNotIn("Marie", content)

    def test_export_does_not_contain_last_name(self):
        r = self.client.get(reverse("accounts:export_data"))
        content = r.content.decode()
        self.assertNotIn("last_name", content)
        self.assertNotIn("Curie", content)
