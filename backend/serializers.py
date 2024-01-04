# Верстальщик
from django.contrib.auth import authenticate
from django.db.models import Q
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
    STATUS_CHOICES,
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


class OrderSerializer(serializers.ModelSerializer):
    ordered_items = OrderItemSerializer(read_only=True, many=True)
    items = OrderItemSerializer(write_only=True, many=True)
    total_sum = serializers.IntegerField(read_only=True)
    contact = ContactSerializer(read_only=True)
    status = serializers.ChoiceField(choices=STATUS_CHOICES, required=False)

    class Meta:
        model = Order
        fields = (
            "id",
            "ordered_items",
            "status",
            "date_time",
            "total_sum",
            "contact",
            "items",
        )
        read_only_fields = ("id",)

    def validate(self, data):
        items = data["items"]
        for item in items:
            product_info = item.get("product_info")
            quantity = item.get("quantity")
            product = ProductInfo.objects.filter(id=product_info.id).first()
            if not product:
                raise serializers.ValidationError(
                    {"status": "failure", "message": "Такого продукта нет"}
                )
            if quantity <= 0:
                raise serializers.ValidationError(
                    {"status": "failure", "message": "Продукта нет в наличии"}
                )
            if quantity > product.quantity:
                raise serializers.ValidationError(
                    {"status": "failure", "message": "Нет такого количества"}
                )
        return data

    def create(self, validated_data):
        user = self.context["request"].user
        items = validated_data.get("items")
        order = Order.objects.create(user=user, status="basket")
        for item in items:
            product_id = item.get("product_info").id
            quantity = item.get("quantity") or 1
            OrderItem.objects.create(
                order=order, product_info_id=product_id, quantity=quantity
            )
        return order

    def update(self, instance, validated_data):
        items = validated_data.get("items")
        instance.ordered_items.all().delete()
        for item in items:
            product_id = item.get("product_info").id
            quantity = item.get("quantity") or 1
            OrderItem.objects.create(
                order=instance, product_info_id=product_id, quantity=quantity
            )
        instance.status = validated_data.get("status", instance.status)
        instance.save()
        return instance


class OrderConfirmSerializer(serializers.Serializer):
    id = serializers.IntegerField(write_only=True)
    contact_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "contact_id",
        )

    def validate(self, data):
        user = self.context["request"].user
        order_id = data.get("id")
        contact_id = data.get("contact_id")
        contact = Contact.objects.filter(Q(user_id=user.id) & Q(id=contact_id)).first()
        order = Order.objects.filter(Q(id=order_id) & Q(user_id=user.id)).first()
        status = order.status
        if not order:
            raise serializers.ValidationError(
                {"status": "failure", "message": "Такого заказа не существует"}
            )
        if not status == "basket":
            raise serializers.ValidationError(
                {"status": "failure", "message": "Неверный статус заказа"}
            )
        if not contact.city:
            raise serializers.ValidationError(
                {"status": "failure", "message": "Не указан город"}
            )
        if not contact.street:
            raise serializers.ValidationError(
                {"status": "failure", "message": "Не указана улица"}
            )
        if not contact.house:
            raise serializers.ValidationError(
                {"status": "failure", "message": "Не указано строение"}
            )
        if not contact.phone:
            raise serializers.ValidationError(
                {"status": "failure", "message": "Не указан номер телефона"}
            )
        order.contact = contact
        return order


class PartnerUpdateSerializer(serializers.Serializer):
    url = serializers.URLField(write_only=True, required=True)
