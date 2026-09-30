from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),

    path("admin-portal/", views.admin_portal, name="admin_portal"),
    path("admin-portal/mobile/", views.admin_portal_mobile, name="admin_portal_mobile"),

    path("products/", views.products, name="products"),
    path("products/add/", views.product_add, name="product_add"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),

    path("suppliers/", views.suppliers, name="suppliers"),
    path("suppliers/add/", views.supplier_add, name="supplier_add"),

    path("staff/", views.staff, name="staff"),
    path("staff/add/", views.staff_add, name="staff_add"),

    path("billing/", views.billing, name="billing"),
    path("billing/checkout/", views.checkout, name="checkout"),
    path("billing/invoice/<int:pk>/", views.invoice, name="invoice"),

    path("returns/", views.returns, name="returns"),
    path("returns/<int:pk>/process/", views.process_return, name="process_return"),

    path("ledger/", views.ledger, name="ledger"),
    path("reports/", views.reports, name="reports"),
]
