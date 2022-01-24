from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Follow, Group, Post

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.author = User.objects.create_user(username='author')
        cls.author_client = Client()
        cls.auth_user = User.objects.create_user(username='AuthorisedUser')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.auth_user)
        cls.follower = User.objects.create_user(username='follower')
        cls.follower_client = Client()
        Follow.objects.create(
            author=cls.author,
            user=cls.follower,
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

    # def setUp(self):
    #    self.authorized_client.force_login(self.auth_user)

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
        for address in public_urls:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_public_urls_use_correct_templates(self):
        """Общедоступные страницы использую соответствующие шаблоны."""
        templates_url_names = {
            'posts/index.html': '/',
            'posts/group_list.html': f'/group/{self.group.slug}/',
            'posts/profile.html': f'/profile/{self.auth_user.username}/',
            'posts/post_detail.html': f'/posts/{self.post.pk}/',
        }
        for template, address in templates_url_names.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_urls_for_authorized_users_exist_at_desired_location(self):
        """Страницы для авторизованных пользователей доступны."""
        urls_for_auth_users = (
            '/create/',
            '/follow/',
        )
        for address in urls_for_auth_users:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_for_authorized_users_use_correct_templates(self):
        """Страницы для авторизованных пользователей
        используют соответствующие шаблоны.
        """
        templates_url_names = {
            'posts/create_post.html': '/create/',
            'posts/follow.html': '/follow/',
        }
        for template, address in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_urls_redirect_authorized_users_to_desired_pages(self):
        """Страницы перенаправляют авторизованного пользователя
        на соответсвующие адреса.
        """
        url_redirect_names = {
            f'/posts/{self.post.pk}/comment/': f'/posts/{self.post.pk}/',
            f'/profile/{self.author.username}/follow/':
                f'/profile/{self.author.username}/',
            f'/profile/{self.author.username}/unfollow/':
                f'/profile/{self.author.username}/',
        }
        for address, redirect_adress in url_redirect_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address, follow=True)
                self.assertRedirects(response, redirect_adress)

    def test_urls_redirect_anonymous_to_auth_login(self):
        """Страницы для авторизованных пользователей перенаправляют
        анонимных пользователей на страницу логина.
        """
        urls_for_auth_users = {
            '/create/',
            f'/posts/{self.post.pk}/comment/',
            '/follow/',
            f'/profile/{self.author.username}/follow/',
            f'/profile/{self.author.username}/unfollow/',
        }
        for address in urls_for_auth_users:
            with self.subTest(address=address):
                response = self.guest_client.get(address, follow=True)
                self.assertRedirects(response, '/auth/login/?next=' + address)

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
