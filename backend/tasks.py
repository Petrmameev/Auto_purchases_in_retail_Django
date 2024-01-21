from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task()
def new_user_registered_signal_mail_task(email):
    # token, _ = ConfirmEmailToken.objects.get_or_create(user=user)

    send_mail(
        # f"Password Reset Token for {user.email}",
        f"Регистрация в Нашем магазине",
        # message:
        # token.key,
        f"Вы были зарегестрированы",
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [email],
        fail_silently=False,
    )


@shared_task()
def new_order_signal_user_task(email):
    send_mail(
        f"Благодарим за заказ",
        # message:
        f"Ваш заказ сформирован",
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [email],
        fail_silently=False,
    )


@shared_task()
def new_order_signal_admin_task():
    send_mail(
        f"У Вас новый заказ",
        # message:
        f"Все подробности в админ-панели",
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [settings.EMAIL_HOST_USER],
        fail_silently=False,
    )
