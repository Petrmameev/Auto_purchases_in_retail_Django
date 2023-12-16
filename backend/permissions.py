from rest_framework import permissions


class Owner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class Shop(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.type == "shop"
