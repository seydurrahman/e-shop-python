from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    # Authentication related urls
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    # products related urls
    path("", views.home, name="home"),
    path("products/", views.product_list, name="product_list"),
    path(
        "products/<slug:category_slug>/",
        views.product_list,
        name="product_list_by_category",
    ),
    path("products/detail/<slug:slug>/", views.product_detail, name="product_detail"),
    path("rate/<int:product_id>/", views.rate_product, name="rate_product"),
    # cart related urls
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart_remove"),
    path("cart/update/<int:product_id>/", views.cart_update, name="cart_update"),
    # checkout related urls
    path("checkout/", views.checkout, name="checkout"),
    path("payment/process/", views.payment_process, name="payment_process"),
    path(
        "payment/success/<int:order_id>/", views.payment_success, name="payment_success"
    ),
    path("payment/notify/<int:order_id>/", views.payment_notify, name="payment_notify"),
    path("payment/fail/<int:order_id>/", views.payment_fail, name="payment_fail"),
    path("payment/cancel/<int:order_id>/", views.payment_cancel, name="payment_cancel"),
    # profile
    path("profile/", views.profile, name="profile"),
    # admin dashboard
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/sales/api/", views.sales_metrics_api, name="sales_metrics_api"),
    path(
        "dashboard/orders/report/",
        views.admin_orders_report,
        name="admin_orders_report",
    ),
]
