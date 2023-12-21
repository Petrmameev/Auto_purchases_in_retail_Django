# Верстальщик
from django.contrib.auth import authenticate
from rest_framework import serializers

from backend.models import (
    Category,
    Contact,
    Order,
    OrderItem,
    Product,
    ProductInfo,
    ProductParameter,
    Shop,
    User,
)


class NewUserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "company",
            "position",
            "password",

        )
        read_only_fields = ("id",)

    def create(self, data):
        password = data.pop("password")
        user = User(**data)
        user.set_password(password)
        user.save()
        return user


class LoginAccountSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    password = serializers.CharField(max_length=20, required=True, write_only=True)

    def validate(self, data):
        email = data["email"]
        password = data["password"]
        user = authenticate(username=email, password=password)
        if user is None or not user.is_active:
            raise serializers.ValidationError(
                {"status": "Failure", "message": "Неверное имя пользователя или пароль"}
            )
        return user


class PartnerStatusSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=30, required=False)
    status = serializers.BooleanField(default=True)
    url = serializers.URLField(required=False)
    file_name = serializers.CharField(max_length=50, required=False)

    class Meta:
        model = Shop
        fields = (
            "id",
            "name",
            "status",
            "url",
            "file_name",
        )
        read_only_fields = ("id",)


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = (
            "id",
            "city",
            "street",
            "house",
            "structure",
            "building",
            "apartment",
            "user",
            "phone",
        )
        read_only_fields = ("id",)
        extra_kwargs = {"user": {"write_only": True}}


class AccountDetailsSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(read_only=True, many=True)

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "company",
            "position",
            "contacts",
            "type",
        )
        read_only_fields = ("id",)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = (
            "id",
            "name",
        )
        read_only_fields = ("id",)


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = (
            "id",
            "name",
            "status",
        )
        read_only_fields = ("id",)


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = (
            "name",
            "category",
        )


class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        fields = (
            "parameter",
            "value",
        )


class ProductInfoSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_parameters = ProductParameterSerializer(read_only=True, many=True)

    class Meta:
        model = ProductInfo
        fields = (
            "id",
            "model",
            "product",
            "shop",
            "quantity",
            "price",
            "price_rrc",
            "product_parameters",
        )
        read_only_fields = ("id",)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_info",
            "quantity",
            "order",
        )
        read_only_fields = ("id",)
        extra_kwargs = {"order": {"write_only": True}}


class OrderSerializer(serializers.Serializer):
    ordered_items = OrderItemSerializer(read_only=True, many=True)
    items = OrderItemSerializer(write_only=True, many=True)
    total_sum = serializers.IntegerField(read_only=True)
    contact = ContactSerializer(read_only=True)
    status = serializers.CharField(required=False)

    class Meta:
        model = Order
        fields = (
            "id",
            "ordered_items",
            "status",
            "dt",
            "total_sum",
            "contact",
            "items",
        )
        read_only_fields = ("id",)

    #         Валидировать данные

    def create(self, data):
        user = self.context["request"].user
        items = data.pop("items")
        order, _ = Order.objects.get_or_create(**data, user_id=user.id, status="basket")
        for item in items:
            product_id = item.get("product_info")
            quantity = item.get("quantity, 1")
            OrderItem.objects.update_or_create(
                order=order, product_info=product_id, defaults={"quantity: quantity"}
            )
        return order

    def update(self, instance, data):
        instance.ordered_items.all().delete()
        instance = super().create(**data)
        return instance


class OrderConfirmSerializer(serializers.Serializer):
    id = serializers.IntegerField(write_only=True)
    contact = serializers.IntegerField(write_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "contact",
        )

    #         Валидировать данные
