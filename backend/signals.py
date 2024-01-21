# from django.conf import settings
# from django.core.mail import EmailMultiAlternatives, send_mail
from django.dispatch import Signal

# from django_rest_passwordreset.signals import reset_password_token_created
from backend.tasks import (
    new_user_registered_signal_mail_task,
    new_order_signal_user_task,
    new_order_signal_admin_task,
)
from backend.models import User
from django.conf import settings

new_user_registered = Signal()

new_order = Signal()


def new_user_registered_signal_mail(user):
    """
    отправляем письмо с подтрердждением почты
    """
    new_user_registered_signal_mail_task.delay(user.email)


def new_order_signal_user(user):
    """
    отправяем письмо с подтверждением заказа
    """
    new_order_signal_user_task.delay(user.email)


def new_order_signal_admin():
    """
    отправяем письмо админу о заказе
    """
    new_order_signal_admin_task.delay()
