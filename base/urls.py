from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.custom_login, name="login"),
    path("logout/", views.custom_logout, name="logout"),

    path("admin-register/", views.admin_register, name="admin_register"),
    path("roommate-register/", views.roommate_register, name="roommate_register"),

    path("approve-roommates/", views.approve_roommates, name="approve_roommates"),
    path("userpage/", views.userpage, name="userpage"),
    # path('requests',views.approve,name="approve")
    path("admin_rent_dashboard",views.admin_rent_dashboard,name="admin_rent_dashboard")
]
