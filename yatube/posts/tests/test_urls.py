from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

    def setUp(self):
        self.guest_client = Client()
        self.author_client = Client()
        self.auth_user = User.objects.create_user(username='AuthorisedUser')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.auth_user)

    def test_unexisting_url(self):
        """Запрос к несуществующей странице."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_public_urls_exist_at_desired_locations(self):
        """Проверка доступности публичных адресов."""
        public_urls = (
            '/',
            f'/group/{self.group.slug}/',
            f'/profile/{self.auth_user.username}/',
            f'/posts/{self.post.pk}/',
        )
        for adress in public_urls:
            with self.subTest(adress=adress):
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_public_urls_use_correct_templates(self):
        """Общедоступные страницы использую соответствующие шаблоны."""
        templates_url_names = {
            'posts/index.html': '/',
            'posts/group_list.html': f'/group/{self.group.slug}/',
            'posts/profile.html': f'/profile/{self.auth_user.username}/',
            'posts/post_detail.html': f'/posts/{self.post.pk}/',
        }
        for template, adress in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.guest_client.get(adress)
                self.assertTemplateUsed(response, template)

    def test_post_create_url_exists_at_desired_location(self):
        """Страница /create/ доступна авторизованному пользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_url_uses_correct_template(self):
        """Страница /create/ использует шаблон posts/create_post.html."""
        response = self.authorized_client.get('/create/')
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_post_create_url_redirects_anonymous_on_auth_login(self):
        """Страница /create/ перенаправит анонимного пользователя
        на страницу логина.
        """
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_post_edit_url_exists_at_desired_location(self):
        """Страница /posts/<post_id>/edit/ доступна автору."""
        self.author_client.force_login(self.author)
        response = self.author_client.get(f'/posts/{self.post.pk}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_url_uses_correct_template(self):
        """Страница /posts/<post_id>/edit/ использует
        шаблон posts.create_post.html.
        """
        self.author_client.force_login(self.author)
        response = self.author_client.get(f'/posts/{self.post.pk}/edit/')
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_post_edit_url_redirects_non_author_on_post_details(self):
        """Страница /posts/<post_id>/edit/ перенаправляет не автора
        на страницу /posts/<post_id>/.
        """
        response = self.authorized_client.get(f'/posts/{self.post.pk}/edit/')
        self.assertRedirects(response, f'/posts/{self.post.pk}/')
