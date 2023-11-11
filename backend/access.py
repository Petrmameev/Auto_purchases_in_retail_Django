from rest_framework import permissions

class Owner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.user


class Shop(permissions.BasePermission):
    def has_permission(self, request, view):
        _type = request.user.type
        return _type == "shop"