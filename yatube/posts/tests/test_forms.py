import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import CommentForm, PostForm
from ..models import Comment, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.form = PostForm()
        cls.author = User.objects.create_user(username='author')
        cls.guest_client = Client()
        cls.author_client = Client()
        cls.author_client.force_login(cls.author)
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded_image = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Первый пост'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        """Валидная форма создаёт новый пост."""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.pk,
            'image': self.uploaded_image,
        }
        response = self.author_client.post(
            reverse('posts:create_post'),
            data=form_data,
            follow=True
        )
        last_post = Post.objects.first()
        self.assertRedirects(
            response, reverse('posts:profile',
                              kwargs={'username': self.author.username}))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(last_post.text, form_data['text'])
        self.assertEqual(last_post.group.pk, form_data['group'])
        self.assertEqual(last_post.author, self.author)

    def test_edit_post(self):
        """Валидная форма редактирует пост."""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Новый текст',
            'group': self.group.pk,
        }
        post_id = self.post.pk
        response = self.author_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post_id}),
            data=form_data,
            follow=True
        )
        edited_post = Post.objects.get(pk=post_id)
        self.assertRedirects(response,
                             reverse('posts:post_detail',
                                     kwargs={'post_id': post_id}))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), post_count)
        self.assertEqual(edited_post.text, form_data['text'])
        self.assertEqual(edited_post.group.pk, form_data['group'])
        self.assertEqual(edited_post.author, self.author)

    def test_guest_user_cannot_create_post(self):
        """Неавторизованный пользователь
        не может опубликовать пост.
        """
        post_count = Post.objects.count()
        form_data = {
            'text': 'Новый текст',
            'group': self.group.pk,
        }
        response = self.guest_client.post(
            reverse('posts:create_post'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('users:login') + '?next=' + reverse('posts:create_post'))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), post_count)


class CommentCreateTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.form = CommentForm()
        cls.author = User.objects.create_user(username='author')
        cls.commentator = User.objects.create_user(username='commentator')
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.commentator)
        cls.post = Post.objects.create(
            author=cls.author,
            text='Первый пост'
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.author,
            text='Текст комментария'
        )

    def test_comment_create(self):
        """Валидная форма создаёт новый комментарий."""
        comment_count = self.post.comments.count()
        form_data = {
            'text': 'Текст нового комментария'
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        last_comment = self.post.comments.last()
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(self.post.comments.count(), comment_count + 1)
        self.assertEqual(last_comment.text, form_data['text'])
        self.assertEqual(last_comment.author, self.commentator)
        self.assertEqual(last_comment.post, self.post)

    def test_unauthorized_user_cannot_comment(self):
        """Неавторизованный пользователь не может комментировать пост."""
        comment_count = self.post.comments.count()
        form_data = {
            'text': 'Текст нового комментария'
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('users:login') + '?next='
            + reverse('posts:add_comment', kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(self.post.comments.count(), comment_count)
