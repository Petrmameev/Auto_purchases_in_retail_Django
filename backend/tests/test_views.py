from django.test import TestCase
from rest_framework.test import APIClient
from backend.models import User
import django
from django.conf import settings

django.setup()
settings.configure()


class NewUserRegistrationTest(TestCase):
    def setup(self):
        self.client = APIClient()

    def test_user_registration(self):
        data = {
            "first_name": "Petr",
            "last_name": "Mameev",
            "email": "petr@mail.ru",
            "company": "D",
            "position": "K",
            "password": "admin123admin",
        }
        response = self.client.post("/user/register", data)

        self.assertEqual(response.status_code, 201)

        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.first_name, "Petr")
        self.assertEqual(user.last_name, "Mameev")
        self.assertEqual(user.email, "petr@mail.ru")
        self.assertEqual(user.company, "D")
        self.assertEqual(user.position, "K")
        self.assertEqual(user.password, "admin123admin")

    def login_success_test(self):
        data = {"email": "petr@mail.ru", "password": "admin123admin"}
        user = User.objects.create_user(**data)
        response = self.client.post("user/login", data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Token", response.data)
        self.assertEqual(response.data["Status"], "Success")

    def login_failed_test(self):
        data = {"email": "pppppetr@mail.ru", "password": "aaaadmin123admin"}
        user = User.objects.create_user(**data)
        response = self.client.post("user/login", data)
        self.assertEqual(response.status_code, 401)

    def login_failed_clear_field_test(self):
        data = {
            "email": "pppppetr@mail.ru",
        }
        user = User.objects.create_user(**data)
        response = self.client.post("user/login", data)
        self.assertEqual(response.status_code, 400)
