from django.urls import path

from backend.views import (
    AccountDetailsView,
    BasketView,
    CategoryView,
    ContactView,
    LoginAccountView,
    NewUserRegistrationView,
    OrderView,
    OrderConfirmView,
    PartnerOrdersView,
    PartnerUpdateFileView,
    PartnerUpdateUrlView,
    ProductInfoView,
    ShopView,
)

app_name = "backend"
urlpatterns = [
    path(
        "partner/update/file",
        PartnerUpdateFileView.as_view(),
        name="partner-update-file",
    ),
    path(
        "partner/update/url", PartnerUpdateUrlView.as_view(), name="partner-update-url"
    ),
    path("partner/orders", PartnerOrdersView.as_view(), name="partner-orders"),
    path("user/register", NewUserRegistrationView.as_view(), name="user-register"),
    path("user/details", AccountDetailsView.as_view(), name="user-details"),
    path("user/contact", ContactView.as_view(), name="user-contact"),
    path("user/login", LoginAccountView.as_view(), name="user-login"),
    path("categories", CategoryView.as_view(), name="categories"),
    path("shops", ShopView.as_view(), name="shops"),
    path("products", ProductInfoView.as_view(), name="shops"),
    path("basket", BasketView.as_view(), name="basket"),
    path("order", OrderView.as_view(), name="order"),
    path("order/confirm", OrderConfirmView.as_view(), name="order_confirm"),
]
