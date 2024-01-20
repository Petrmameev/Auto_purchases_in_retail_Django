from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.tokens import get_token_generator

USER_TYPE_CHOICES = (
    ("shop", "Магазин"),
    ("buyer", "Покупатель"),
)

STATUS_CHOICES = (
    ("basket", "Статус корзины"),
    ("new", "Новый"),
    ("confirmed", "Подтвержден"),
    ("assembled", "Собран"),
    ("sent", "Отправлен"),
    ("delivered", "Доставлен"),
    ("canceled", "Отменен"),
)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Please enter your email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser mast have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser mast have is_superuser=True")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    USERNAME_FIELD = "email"
    objects = UserManager()
    REQUIRED_FIELDS = []
    email = models.EmailField(_("e-mail address"), unique=True)
    company = models.CharField(
        max_length=30, verbose_name="Название компании", blank=True
    )
    position = models.CharField(max_length=30, verbose_name="Должность", blank=True)
    username_validator = UnicodeUsernameValidator()
    username = models.CharField(
        _("username"),
        max_length=40,
        help_text=_(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
        validators=[username_validator],
        error_messages={"unique": _("A user with username already exists")},
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    type = models.CharField(
        max_length=5,
        verbose_name="Тип пользователя",
        choices=USER_TYPE_CHOICES,
        default="buyer",
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Список пользователей"
        ordering = ("email",)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Shop(models.Model):
    name = models.CharField(
        max_length=50, unique=True, verbose_name="Название магазина"
    )
    url_shop = models.URLField(verbose_name="Ссылка", null=True, blank=True)
    user = models.OneToOneField(
        User,
        verbose_name="Пользователь",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    status = models.BooleanField(verbose_name="Статус получения заказов", default=True)

    class Meta:
        verbose_name = "Магазин"
        verbose_name_plural = "Список магазинов"
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} {self.user} {self.status}"


class Category(models.Model):
    name_category = models.CharField(max_length=50, verbose_name="Название категории")
    shops = models.ManyToManyField(
        Shop, verbose_name="Магазины", related_name="Категории", blank=True
    )

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ("name_category",)

    def __str__(self):
        return self.name_category


class Product(models.Model):
    name = models.CharField(max_length=70, verbose_name="Название товара")
    category = models.ForeignKey(
        Category,
        verbose_name="Категория",
        related_name="Товары",
        blank=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Список товаров"
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} ({self.category})"


class ProductInfo(models.Model):
    model = models.CharField(max_length=30, verbose_name="Модель товара", blank=True)
    external_id = models.PositiveIntegerField(verbose_name="Внешний идентификатор инфы")
    product = models.ForeignKey(
        Product,
        verbose_name="Товар",
        related_name="product_info",
        on_delete=models.CASCADE,
    )
    shop = models.ForeignKey(
        Shop,
        verbose_name="Магазин",
        related_name="product_info",
        on_delete=models.CASCADE,
    )
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    price = models.PositiveIntegerField(verbose_name="Цена")
    price_rrc = models.PositiveIntegerField(
        verbose_name="Рекомендуемая розничная цена", default=0
    )

    class Meta:
        verbose_name = "Информация о продукте"
        verbose_name_plural = "Информация о продуктах"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "shop", "external_id"], name="unique_product_info"
            ),
        ]

    def __str__(self):
        return f"{self.model} ({self.product} {self.quantity} {self.price} {self.price_rrc})"


class Parameter(models.Model):
    name_parameter = models.CharField(max_length=100, verbose_name="Название параметра")

    class Meta:
        verbose_name = "Параметр"
        verbose_name_plural = "Список параметров"
        ordering = ("name_parameter",)

    def __str__(self):
        return self.name_parameter


class ProductParameter(models.Model):
    product_info = models.ForeignKey(
        ProductInfo,
        verbose_name="Информация о товаре",
        related_name="product_parameters",
        blank=True,
        on_delete=models.CASCADE,
    )
    parameter = models.ForeignKey(
        Parameter,
        verbose_name="Параметр",
        related_name="product_parameters",
        blank=True,
        on_delete=models.CASCADE,
    )
    value = models.CharField(max_length=300, verbose_name="Значение")

    class Meta:
        verbose_name = "Параметры"
        verbose_name_plural = "Список параметров"
        constraints = [
            models.UniqueConstraint(
                fields=["product_info", "parameter"], name="unique_product_parameter"
            ),
        ]

    def __str__(self):
        return f"{self.product_info} ({self.parameter} {self.value}"


class Contact(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name="Контакты",
        related_name="Пользователь",
        blank=True,
        on_delete=models.CASCADE,
    )
    city = models.CharField(max_length=30, verbose_name="Город")
    street = models.CharField(max_length=30, verbose_name="Улица")
    house = models.CharField(max_length=30, verbose_name="Дом")
    structure = models.CharField(max_length=30, verbose_name="Корпус", blank=True)
    building = models.CharField(max_length=30, verbose_name="Строение", blank=True)
    apartment = models.CharField(max_length=30, verbose_name="Квартирва", blank=True)
    phone = models.CharField(max_length=20, verbose_name="Телефон")

    class Meta:
        verbose_name = "Контакт пользователя"
        verbose_name_plural = "Список контактов пользователяя"

    def __str__(self):
        return f"{self.city} {self.street} {self.house}"


class Order(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name="Пользователь",
        related_name="Заказ",
        on_delete=models.CASCADE,
    )

    date_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=15, verbose_name="Статус", choices=STATUS_CHOICES
    )
    contact = models.ForeignKey(
        Contact,
        verbose_name="Контакт",
        related_name="Заказ",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Список заказов"
        ordering = ("-date_time",)

    def __str__(self):
        return f"{self.date_time} {self.status}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        verbose_name="Заказ",
        related_name="ordered_items",
        on_delete=models.CASCADE,
    )
    product_info = models.ForeignKey(
        ProductInfo,
        verbose_name="Информация о продукте",
        related_name="ordered_items",
        on_delete=models.CASCADE,
    )
    quantity = models.PositiveIntegerField(verbose_name="Количество")

    class Meta:
        verbose_name = "Заказанный товар"
        verbose_name_plural = "Список заказанных товаров"
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product_info"], name="unique_order_item"
            ),
        ]

    def __str__(self):
        return f"{self.order} ({self.product_info} {self.quantity}"


class ConfirmEmailToken(models.Model):
    pass


#     class Meta:
#         verbose_name = "Токен подтверждения Email"
#         verbose_name_plural = "Токены подтверждения Email"
#
#     @staticmethod
#     def generate_key():
#         """generates a pseudo random code using os.urandom and binascii.hexlify"""
#         return get_token_generator().generate_token()
#
#     user = models.ForeignKey(
#         User,
#         related_name="confirm_email_tokens",
#         on_delete=models.CASCADE,
#         verbose_name=_("The User which is associated to this password reset token"),
#     )
#     created_at = models.DateTimeField(
#         auto_now_add=True, verbose_name=_("When was this token generated")
#     )
#     key = models.CharField(_("key"), max_length=64, db_index=True, unique=True)
#
#     def save(self, *args, **kwargs):
#         if not self.key:
#             self.key = self.generate_key()
#         return super(ConfirmEmailToken, self).save(*args, **kwargs)
#
#     def __str__(self):
#         return "Password reset token for user {user}".format(user=self.user)
