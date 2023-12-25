from distutils.util import strtobool
import os
import yaml
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.db.models import F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from requests import get
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from ujson import loads as load_json
from yaml import Loader
from yaml import load as load_yaml

from backend.permissions import Owner, IsShop
from backend.models import (
    Category,
    Contact,
    Order,
    OrderItem,
    Parameter,
    Product,
    ProductInfo,
    ProductParameter,
    Shop,
    User,
)
from backend.serializers import (
    AccountDetailsSerializer,
    CategorySerializer,
    ContactSerializer,
    LoginAccountSerializer,
    NewUserRegistrationSerializer,
    OrderConfirmSerializer,
    OrderItemSerializer,
    OrderSerializer,
    PartnerStatusSerializer,
    ProductInfoSerializer,
    ShopSerializer,
)
from backend.signals import (
    new_order,
    new_user_registered,
    new_user_registered_signal_mail,
)


class NewUserRegistrationView(APIView):
    """
    Класс для создания пользователя
    """

    serializer_class = NewUserRegistrationSerializer
    queryset = User.objects.all()

    def post(self, request, *args, **Kwargs):
        serializer = NewUserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # new_user_registered_signal_mail(user)
            response = {
                "status": "Success",
                "message": "Учетная запись создана, на почту отправлено оповещение о регистрации",
            }
            return Response(response, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AccountDetailsView(APIView):
    """
    Класс для работы c данными пользователя
    """

    serializer = AccountDetailsSerializer
    queryset = User.objects.prefetch_related()
    permission_classes = [IsAuthenticated, Owner]

    def get(self, request):
        user = request.user
        serializer = AccountDetailsSerializer(instance=user)
        return Response(serializer.data)

    def patch(self, request):
        user = request.user
        data = request.data
        serializer = AccountDetailsSerializer(instance=user, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAccountView(APIView):
    serializer_class = LoginAccountSerializer
    """
    Класс для авторизации пользователей
    """

    # Авторизация методом POST
    def post(self, request):
        serializer = LoginAccountSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            token, _ = Token.objects.get_or_create(user=user)
            response = {"Status": "Success", "Token": token.key}
            return Response(response, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)


class CategoryView(ListAPIView):
    """
    Класс для просмотра категорий
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ShopView(ListAPIView):
    """
    Класс для просмотра списка магазинов
    """

    queryset = Shop.objects.filter(status=True)
    serializer_class = ShopSerializer


class ProductInfoView(APIView):
    """
    Класс для поиска товаров
    """

    def get(self, request, *args, **kwargs):
        query = Q(shop__status=True)
        shop_id = request.query_params.get("shop_id")
        category_id = request.query_params.get("category_id")
        if shop_id:
            query = query & Q(shop_id=shop_id)
        if category_id:
            query = query & Q(product__category__id=category_id)
        queryset = (
            ProductInfo.objects.filter(query)
            .select_related("shop", "product__category")
            .prefetch_related("product_parameters__parameter")
            .distinct()
        )

        serializer = ProductInfoSerializer(queryset, many=True)

        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = ProductInfoSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(
                {"status": "success", "message": "Информация о товаре сформирована"},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BasketView(APIView):
    """
    Класс для работы с корзиной пользователя
    """

    permission_classes = [IsAuthenticated]
    # queryset = Order.objects.filter(status=True)
    serializer_class = OrderSerializer

    # получить корзину
    def get(self, requset, *args, **kwargs):
        basket = (
            Order.objects.filter(user=self.request.user, status="basket")
            .prefetch_related(
                "ordered_items__product_info__product__category",
                "ordered_items__product_info__product_parameters__parameter",
            )
            .annotate(
                total_sum=Sum(
                    F("ordered_items__quantity")
                    * F("ordered_items__product_info__price")
                )
            )
            .distinct()
        )

        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # добавить позиции в корзину
    def post(self, request, *args, **kwargs):
        order, _ = Order.objects.get_or_create(user=self.request.user, status="basket")
        serializer = OrderSerializer(
            order, data=request.data, context={"request": request}
        )
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(
                {"status": "success", "messasge": "Товар добавлен в корзину"},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # удалить товары из корзины
    def delete(self, request):
        order = Order.objects.filter(user=self.request.user, status="basket").first()
        if order is None:
            return Response(
                {"status": "failure", "message": "Корзина уже пуста"},
                status=status.HTTP_404_NOT_FOUND,
            )
        order.delete()
        return Response(
            {"status": "success", "message": "Корзина очищена"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # редактировать корзину

    def put(self, request, *args, **kwargs):
        serializer = OrderSerializer(data=request.data, context={"request": request})
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(
                {"status": "success", "message": "Корзина отредактирована"},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PartnerUpdateView(APIView):
    """
    Класс для обновления прайса от поставщика
    """

    permission_classes = [IsAuthenticated, IsShop]

    def post(self, request, *args, **kwargs):
        data_1 = "./data/shop1.yaml"
        data_2 = "./data/shop2.yaml"
        data = [data_1, data_2]
        for i in data:
            with open(i, "r", encoding="utf-8") as updatefile:
                try:
                    data = yaml.safe_load(updatefile)
                except yaml.YAMLError as yamlerror:
                    print(yamlerror)
                    return Response(
                        {"Status": "Failure", "Message": "Ошибка загрузки файла"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            shop, _ = Shop.objects.get_or_create(
                name=data["shop"]
                # , user_id=request.user.id
            )

            for category in data["categories"]:
                category_object, _ = Category.objects.get_or_create(
                    id=category["id"], name=category["name"]
                )
                category_object.shops.add(shop.id)
                category_object.save()

            ProductInfo.objects.filter(shop_id=shop.id).delete()

            for item in data["goods"]:
                product, _ = Product.objects.get_or_create(
                    name=item["name"], category_id=item["category"]
                )

                product_info = ProductInfo.objects.create(
                    product_id=product.id,
                    external_id=item["id"],
                    model=item["model"],
                    price=item["price"],
                    price_rrc=item["price_rrc"],
                    quantity=item["quantity"],
                    shop_id=shop.id,
                )
                for name, value in item["parameters"].items():
                    parameter_object, _ = Parameter.objects.get_or_create(
                        name_parameter=name
                    )
                    ProductParameter.objects.create(
                        product_info_id=product_info.id,
                        parameter_id=parameter_object.id,
                        value=value,
                    )

        return Response(
            {"Status": "Success", "Message": "Прайс обновлен"},
            status=status.HTTP_200_OK,
        )


class PartnerStatusView(RetrieveUpdateAPIView):
    """
    Класс для работы со статусом поставщика
    """

    queryset = Shop.objects.all()
    serializer_class = PartnerStatusSerializer
    permission_classes = [IsAuthenticated, Owner]
    lookup_field = "id"


class PartnerOrdersView(APIView):
    """
    Класс для получения заказов поставщиками
    """

    permission_classes = [IsAuthenticated, IsShop]
    serializer_class = OrderSerializer

    #
    def get(self, request, *args, **kwargs):
        order = (
            Order.objects.filter(
                ordered_items__product_info__shop__user_id=request.user.id
            )
            .exclude(status="basket")
            .prefetch_related(
                "ordered_items__product_info__product__category",
                "ordered_items__product_info__product_parameters__parameter",
            )
            .select_related("contact")
            .annotate(
                total_sum=Sum(
                    F("ordered_items__quantity")
                    * F("ordered_items__product_info__price")
                )
            )
            .distinct()
        )

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)


class ContactView(APIView):
    """
    Класс для работы с контактами покупателей
    """

    permission_classes = [IsAuthenticated, Owner]

    def post(self, request, *args, **kwargs):
        request.data["user"] = request.user.id
        serializer = ContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request, *args, **kwargs):
        request.data["user"] = request.user.id
        # instance = self.get_object(contact_id)
        serializer = ContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        contact = Contact.objects.all()
        contact.delete()
        return Response(
            {"Status": "Success", "Message": "Контакты удалены"},
            status=status.HTTP_204_NO_CONTENT,
        )


class OrderView(APIView):
    """
    Класс для получения заказов пользователями
    """

    permission_classes = [IsAuthenticated, Owner]
    serializer = OrderSerializer

    # получить мои заказы
    def get(self, request, *args, **kwargs):
        order = (
            Order.objects.filter(user_id=request.user.id)
            .exclude(status="basket")
            .prefetch_related(
                "ordered_items__product_info__product__category",
                "ordered_items__product_info__product_parameters__parameter",
            )
            .select_related("contact")
            .annotate(
                total_sum=Sum(
                    F("ordered_items__quantity")
                    * F("ordered_items__product_info__price")
                )
            )
            .distinct()
        )

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)


class OrderConfirmView(APIView):
    """
    Класс для размещения заказов пользователями
    """

    permission_classes = [IsAuthenticated, Owner]
    serializer = OrderConfirmSerializer

    # разместить заказ из корзины
    def post(self, request, *args, **kwargs):
        serializer = OrderConfirmSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid(raise_exception=True):
            basket = (
                Order.objects.filter(user=self.request.user, status="basket")
                .prefetch_related("ordered_items")
                .annotate(
                    total_sum=Sum(
                        F("ordered_items__quantity")
                        * F("ordered_items__product_info__price")
                    )
                )
                .first()
            )
            response = OrderSerializer(basket)
            user = request.user
            order = serializer.save()
            order.status = "new"
            order.save()
            #     Оповещение о созданном заказе

            return Response(
                {"Status": "Success", "Message": "Заказ создан"},
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
