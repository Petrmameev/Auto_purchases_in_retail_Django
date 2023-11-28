from distutils.util import strtobool

import yaml
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.db.models import F, Q, Sum
from django.http import JsonResponse
from requests import get
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from ujson import loads as load_json
from yaml import Loader
from yaml import load as load_yaml

from backend.access import Owner
from backend.models import (Category, ConfirmEmailToken, Contact, Order,
                            OrderItem, Parameter, Product, ProductInfo,
                            ProductParameter, Shop, User)
from backend.serializers import (AccountDetailsSerializer, CategorySerializer,
                                 ConfirmAccountSerializer, ContactSerializer,
                                 LoginAccountSerializer,
                                 NewUserRegistrationSerializer,
                                 OrderItemSerializer, OrderSerializer,
                                 PartnerStatusSerializer,
                                 ProductInfoSerializer, ShopSerializer)
from backend.signals import (new_order, new_user_registered,
                             new_user_registered_signal_mail)


class NewUserRegistrationView(APIView):
    """
    Класс для создания пользователья
    """

    serializer_class = NewUserRegistrationSerializer
    queryset = User.objects.all()

    def post(self, request, *args, **Kwargs):
        serializer = NewUserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            new_user_registered_signal_mail(user)
            token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
            response = {
                "status": "Success",
                "message": "Учетная запись создана, на почту отправлен токен",
                "token": {token.key},
            }
            return Response(response, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConfirmAccountView(APIView):
    """
    Класс для подтвердения почтового адреса
    """

    serializer_class = ConfirmAccountSerializer

    def post(self, request, *args, **kwargs):
        serializer = ConfirmAccountSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data
            token.user.is_active = True
            token.user.save()
            token.delete()
            response = {"status": "Success", "message": "Аккаунт подтвержден"}
            return Response(response, status=status.HTTP_200_OK)
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

    queryset = (
        ProductInfo.objects.select_related("shop", "product__category")
        .prefetch_related("product_parameters__parameter")
        .distinct()
    )
    serializer_class = ProductInfoSerializer


class BasketView(APIView):
    """
    Класс для работы с корзиной пользователя
    """

    permission_classes = [IsAuthenticated, Owner]
    queryset = Order.objects.filter(status=True)
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
        serializer = OrderSerializer(
            data=self.request.data, context={"request": request}
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
            status=status.HTTP_200_OK,
        )

    # редактировать корзину

    def put(self, request, *args, **kwargs):
        serializer = OrderSerializer(
            data=self.request.data, context={"request": request}
        )
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

    # permission_classes = [IsAuthenticated, Shop]

    def post(self, request, *args, **kwargs):
        with open("./data/shop1.yaml", "r", encoding="utf-8") as updatefile:
            try:
                data = yaml.safe_load(updatefile)
            except yaml.YAMLError as yamlerror:
                print(yamlerror)
                return Response(
                    {"Status": "Failure", "Message": "Ошибка загрузки файла"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        print(data)
        shop, _ = Shop.objects.get_or_create(name=data["shop"], user_id=request.user.id)

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
                parameter_object, _ = Parameter.objects.get_or_create(name=name)
                ProductParameter.objects.create(
                    product_info_id=product_info.id,
                    parameter_id=parameter_object.id,
                    value=value,
                )

        return Response(
            {"Status": "Success", "Message": "Прайс обновлен"},
            status=status.HTTP_200_OK,
        )


class PartnerStatusView(APIView):
    """
    Класс для работы со статусом поставщика
    """

    queryset = Shop.objects.all()
    serializer_class = PartnerStatusSerializer
    permission_classes = [IsAuthenticated, Owner, Shop]


class PartnerOrdersView(APIView):
    """
    Класс для получения заказов поставщиками
    """

    permission_classes = [IsAuthenticated, Shop]
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

    serializer_class = ContactSerializer
    queryset = Contact.objects.prefetch_related()
    permission_classes = [IsAuthenticated, Owner]


class OrderView(APIView):
    """
    Класс для получения и размешения заказов пользователями
    """

    pass


#     # получить мои заказы
#     def get(self, request, *args, **kwargs):
#         authenticated_user(request)
#         order = (
#             Order.objects.filter(user_id=request.user.id)
#             .exclude(status="basket")
#             .prefetch_related(
#                 "ordered_items__product_info__product__category",
#                 "ordered_items__product_info__product_parameters__parameter",
#             )
#             .select_related("contact")
#             .annotate(
#                 total_sum=Sum(
#                     F("ordered_items__quantity")
#                     * F("ordered_items__product_info__price")
#                 )
#             )
#             .distinct()
#         )
#
#         serializer = OrderSerializer(order, many=True)
#         return Response(serializer.data)
#
#     # разместить заказ из корзины
#     def post(self, request, *args, **kwargs):
#         authenticated_user(request)
#         if {"id", "contact"}.issubset(request.data):
#             if request.data["id"].isdigit():
#                 try:
#                     is_updated = Order.objects.filter(
#                         user_id=request.user.id, id=request.data["id"]
#                     ).update(contact_id=request.data["contact"], status="new")
#                 except IntegrityError as error:
#                     print(error)
#                     return JsonResponse(
#                         {"Status": False, "Errors": "Неправильно указаны аргументы"}
#                     )
#                 else:
#                     if is_updated:
#                         new_order.send(sender=self.__class__, user_id=request.user.id)
#                         return JsonResponse({"Status": True})
#
#         return JsonResponse(
#             {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
#         )
