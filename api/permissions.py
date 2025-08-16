from rest_framework import permissions

class IsTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and hasattr(request.user, 'teacher')

class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and hasattr(request.user, 'student')

class IsStudentOrTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and (hasattr(request.user, 'student') or hasattr(request.user, 'teacher'))