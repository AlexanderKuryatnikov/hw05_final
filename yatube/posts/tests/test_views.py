from math import ceil
import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


def assert_post_object_context(post_pages_class, post_object):
    """Проверка контекста поста."""
    post_text = post_object.text
    post_author = post_object.author
    post_group = post_object.group
    pub_date = post_object.pub_date
    image = post_object.image
    post_pages_class.assertEqual(post_text, post_pages_class.post.text)
    post_pages_class.assertEqual(post_author, post_pages_class.author)
    post_pages_class.assertEqual(post_group, post_pages_class.group)
    post_pages_class.assertEqual(pub_date, post_pages_class.post.pub_date)
    post_pages_class.assertEqual(image, post_pages_class.post.image)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.author_client = Client()
        cls.author_client.force_login(cls.author)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded_image = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
            group=cls.group,
            image=uploaded_image
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_pages_use_correct_templates(self):
        """URL-адреса используют соответсвующие шаблоны."""
        pages_names_templates = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.author.username}):
                'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.pk}):
                'posts/post_detail.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.pk}):
                'posts/create_post.html',
            reverse('posts:create_post'): 'posts/create_post.html',
        }
        for reverse_name, template in pages_names_templates.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_shows_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.author_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        assert_post_object_context(self, first_object)

    def test_group_post_shows_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.author_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group.slug}))
        first_object = response.context['page_obj'][0]
        context_group = response.context.get('group')
        assert_post_object_context(self, first_object)
        self.assertEqual(context_group.title, self.group.title)
        self.assertEqual(context_group.slug, self.group.slug)
        self.assertEqual(context_group.description, self.group.description)

    def test_profile_shows_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.author_client.get(reverse(
            'posts:profile', kwargs={'username': self.author.username}))
        first_object = response.context['page_obj'][0]
        assert_post_object_context(self, first_object)
        self.assertEqual(response.context.get('author'), self.author)
        self.assertEqual(response.context.get('post_count'),
                         self.author.posts.count())

    def test_post_detail_shows_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.author_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.pk}))
        post_object = response.context.get('post')
        assert_post_object_context(self, post_object)
        self.assertEqual(response.context.get('post_count'),
                         self.author.posts.count())

    def test_post_create_shows_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.author_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.pk}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_shows_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.author_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.pk}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertEqual(response.context.get('is_edit'), True)


class PaginatorViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        POSTS_TOTAL = 13
        cls.LAST_PAGE = ceil(POSTS_TOTAL / settings.POSTS_PER_PAGE)
        cls.NUMBER_OF_LAST_PAGE_POSTS = (POSTS_TOTAL
                                         - settings.POSTS_PER_PAGE
                                         * (cls.LAST_PAGE - 1))
        Post.objects.bulk_create([Post(author=cls.author,
                                       text=f'Тестовый пост {i}',
                                       group=cls.group,)
                                  for i in range(POSTS_TOTAL)])

    def test_first_index_page_contains_ten_posts(self):
        """На первой странице posts:index должно быть 10 постов."""
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']),
                         settings.POSTS_PER_PAGE)

    def test_second_index_page_contains_three_posts(self):
        """На второй странице posts:index должно быть 3 поста."""
        response = self.client.get(reverse('posts:index')
                                   + f'?page={self.LAST_PAGE}')
        self.assertEqual(len(response.context['page_obj']),
                         self.NUMBER_OF_LAST_PAGE_POSTS)

    def test_first_group_page_contains_ten_posts(self):
        """На первой странице posts:group_list должно быть 10 постов."""
        response = self.client.get(reverse('posts:group_list',
                                           kwargs={'slug': self.group.slug}))
        self.assertEqual(len(response.context['page_obj']),
                         settings.POSTS_PER_PAGE)

    def test_second_group_page_contains_three_posts(self):
        """На первой странице posts:group_list должно быть 3 поста."""
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
            + f'?page={self.LAST_PAGE}')
        self.assertEqual(len(response.context['page_obj']),
                         self.NUMBER_OF_LAST_PAGE_POSTS)

    def test_first_author_page_contains_ten_posts(self):
        """На первой странице posts:profile должно быть 10 постов."""
        response = self.client.get(
            reverse('posts:profile',
                    kwargs={'username': self.author.username}))
        self.assertEqual(len(response.context['page_obj']),
                         settings.POSTS_PER_PAGE)

    def test_second_author_page_contains_three_posts(self):
        """На первой странице posts:profile должно быть 3 поста."""
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': self.author.username})
            + f'?page={self.LAST_PAGE}')
        self.assertEqual(len(response.context['page_obj']),
                         self.NUMBER_OF_LAST_PAGE_POSTS)


class NewPostTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.author_client = Client()
        cls.post_group = Group.objects.create(
            title='Тестовая группа для поста',
            slug='post-group',
            description='Тестовое описание',
        )
        cls.empty_group = Group.objects.create(
            title='Пустая тестовая группа',
            slug='empty-group',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
            group=cls.post_group,
        )

    def test_index_page_contains_post(self):
        """На главной странице отображается новый пост."""
        response = self.client.get(reverse('posts:index'))
        self.assertIn(self.post, response.context['page_obj'])

    def test_profile_page_contains_post(self):
        """На странице автора отображается новый пост."""
        response = self.client.get(reverse('posts:profile',
                                           kwargs={'username': 'author'}))
        self.assertIn(self.post, response.context['page_obj'])

    def test_group_page_contains_post(self):
        """На странице группы отображается новый пост."""
        response = self.client.get(reverse('posts:group_list',
                                           kwargs={'slug': 'post-group'}))
        self.assertIn(self.post, response.context['page_obj'])

    def test_empty_group_page_does_not_contain_post(self):
        """В пустой группе не отображается новый пост."""
        response = self.client.get(reverse('posts:group_list',
                                           kwargs={'slug': 'empty-group'}))
        self.assertNotIn(self.post, response.context['page_obj'])


class CommentViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.author,
            text='Текст комментария'
        )

    def test_post_detail_page_contains_comment(self):
        """Комментарий появляется на странице поста."""
        response = self.client.get(reverse('posts:post_detail',
                                           kwargs={'post_id': self.post.pk}))
        self.assertIn(self.comment, response.context.get('comments'))
