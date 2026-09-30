from decimal import Decimal
from functools import wraps
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProductForm, SupplierForm, StaffCreateForm
from .models import Product, Supplier, StaffProfile, Sale, SaleItem, ProductReturn, LedgerEntry

def is_admin(user):
    return user.is_superuser or (
        hasattr(user, "staff_profile") and user.staff_profile.role == "ADMIN"
    )

def admin_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            messages.error(request, "Admin access required.")
            return redirect("billing")
        return view(request, *args, **kwargs)
    return wrapper

def staff_or_admin(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        return view(request, *args, **kwargs)
    return wrapper

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("dashboard")
        messages.error(request, "Invalid username or password.")
    return render(request, "login.html")

def logout_view(request):
    logout(request)
    return redirect("login")

@staff_or_admin
def dashboard(request):
    if is_admin(request.user):
        return redirect("admin_portal")
    return redirect("billing")

@admin_required
def admin_portal(request):
    context = {
        "product_count": Product.objects.count(),
        "staff_count": User.objects.filter(is_active=True).count(),
        "supplier_count": Supplier.objects.count(),
        "sales_count": Sale.objects.count(),
        "sales_total": Sale.objects.aggregate(v=Sum("total"))["v"] or Decimal("0"),
        "low_stock": Product.objects.filter(active=True, stock__lte=5).order_by("stock")[:8],
        "recent_sales": Sale.objects.select_related("staff").order_by("-created_at")[:8],
    }
    return render(request, "admin/dashboard.html", context)

@admin_required
def admin_portal_mobile(request):
    context = {
        "product_count": Product.objects.count(),
        "staff_count": User.objects.filter(is_active=True).count(),
        "supplier_count": Supplier.objects.count(),
        "sales_count": Sale.objects.count(),
        "sales_total": Sale.objects.aggregate(v=Sum("total"))["v"] or Decimal("0"),
        "low_stock": Product.objects.filter(active=True, stock__lte=5).order_by("stock")[:5],
        "recent_sales": Sale.objects.order_by("-created_at")[:5],
    }
    return render(request, "admin/mobile_dashboard.html", context)

@admin_required
def products(request):
    q = request.GET.get("q", "")
    qs = Product.objects.select_related("supplier").order_by("-created_at")
    if q:
        qs = qs.filter(name__icontains=q) | qs.filter(sku__icontains=q)
    return render(request, "admin/products.html", {"products": qs, "q": q})

@admin_required
def product_add(request):
    form = ProductForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Product added.")
        return redirect("products")
    return render(request, "admin/form.html", {"form": form, "title": "Add Product", "back": "products"})

@admin_required
def product_edit(request, pk):
    obj = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, "Product updated.")
        return redirect("products")
    return render(request, "admin/form.html", {"form": form, "title": "Edit Product", "back": "products"})

@admin_required
def product_delete(request, pk):
    obj = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Product deleted.")
    return redirect("products")

@admin_required
def suppliers(request):
    return render(request, "admin/suppliers.html", {"suppliers": Supplier.objects.order_by("-created_at")})

@admin_required
def supplier_add(request):
    form = SupplierForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Supplier added.")
        return redirect("suppliers")
    return render(request, "admin/form.html", {"form": form, "title": "Add Supplier", "back": "suppliers"})

@admin_required
def staff(request):
    staff_profiles = StaffProfile.objects.select_related("user").order_by("user__username")
    return render(request, "admin/staff.html", {"staff_profiles": staff_profiles})

@admin_required
def staff_add(request):
    form = StaffCreateForm(request.POST or None)
    if form.is_valid():
        user = User.objects.create_user(
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
        )
        StaffProfile.objects.create(
            user=user,
            role=form.cleaned_data["role"],
            phone=form.cleaned_data["phone"],
        )
        messages.success(request, "Staff account created.")
        return redirect("staff")
    return render(request, "admin/form.html", {"form": form, "title": "Add Staff", "back": "staff"})

@staff_or_admin
def billing(request):
    products = Product.objects.filter(active=True, stock__gt=0).order_by("name")
    return render(request, "billing.html", {"products": products})

@staff_or_admin
@transaction.atomic
def checkout(request):
    if request.method != "POST":
        return redirect("billing")

    product_ids = request.POST.getlist("product_id")
    quantities = request.POST.getlist("quantity")
    payment_method = request.POST.get("payment_method", "CASH")
    discount = Decimal(request.POST.get("discount", "0") or "0")

    if not product_ids:
        messages.error(request, "Cart is empty.")
        return redirect("billing")

    subtotal = Decimal("0")
    cart = []

    for pid, qty_raw in zip(product_ids, quantities):
        qty = int(qty_raw)
        product = Product.objects.select_for_update().get(pk=pid)
        if qty <= 0 or qty > product.stock:
            messages.error(request, f"Invalid quantity for {product.name}.")
            return redirect("billing")
        line_total = product.price * qty
        subtotal += line_total
        cart.append((product, qty, line_total))

    discount = max(Decimal("0"), min(discount, subtotal))
    tax = Decimal("0")  # Kept configurable/simple for interview task.
    total = subtotal - discount + tax

    invoice_no = f"INV-{uuid4().hex[:8].upper()}"

    sale = Sale.objects.create(
        invoice_no=invoice_no,
        staff=request.user,
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        total=total,
        payment_method=payment_method,
    )

    for product, qty, line_total in cart:
        SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=qty,
            unit_price=product.price,
            line_total=line_total,
        )
        product.stock -= qty
        product.save(update_fields=["stock"])

    LedgerEntry.objects.create(
        entry_type="SALE",
        reference=invoice_no,
        description=f"Sale through {payment_method}",
        amount=total,
    )

    return redirect("invoice", pk=sale.pk)

@staff_or_admin
def invoice(request, pk):
    sale = get_object_or_404(Sale.objects.select_related("staff").prefetch_related("items__product"), pk=pk)
    return render(request, "invoice.html", {"sale": sale})

@admin_required
def returns(request):
    sale_items = SaleItem.objects.select_related("sale", "product").order_by("-sale__created_at")
    return render(request, "admin/returns.html", {"sale_items": sale_items[:100]})

@admin_required
@transaction.atomic
def process_return(request, pk):
    sale_item = get_object_or_404(SaleItem.objects.select_for_update(), pk=pk)
    if request.method == "POST":
        qty = int(request.POST.get("quantity", "0"))
        reason = request.POST.get("reason", "")
        already_returned = ProductReturn.objects.filter(sale_item=sale_item).aggregate(v=Sum("quantity"))["v"] or 0
        available = sale_item.quantity - already_returned
        if qty <= 0 or qty > available:
            messages.error(request, f"Return quantity must be between 1 and {available}.")
            return redirect("returns")

        ProductReturn.objects.create(
            sale_item=sale_item,
            quantity=qty,
            reason=reason,
            handled_by=request.user,
        )
        product = sale_item.product
        product.stock += qty
        product.save(update_fields=["stock"])

        LedgerEntry.objects.create(
            entry_type="RETURN",
            reference=sale_item.sale.invoice_no,
            description=f"Return: {product.name}",
            amount=-(sale_item.unit_price * qty),
        )
        messages.success(request, "Return processed and stock restored.")
    return redirect("returns")

@admin_required
def ledger(request):
    entries = LedgerEntry.objects.order_by("-created_at")
    totals = entries.aggregate(v=Sum("amount"))["v"] or Decimal("0")
    return render(request, "admin/ledger.html", {"entries": entries[:200], "balance": totals})

@admin_required
def reports(request):
    sales = Sale.objects.all()
    context = {
        "total_sales": sales.aggregate(v=Sum("total"))["v"] or Decimal("0"),
        "invoice_count": sales.count(),
        "items_sold": SaleItem.objects.aggregate(v=Sum("quantity"))["v"] or 0,
        "payment_summary": sales.values("payment_method").annotate(total=Sum("total"), count=Count("id")).order_by("-total"),
        "top_products": SaleItem.objects.values("product__name").annotate(qty=Sum("quantity")).order_by("-qty")[:10],
    }
    return render(request, "admin/reports.html", context)

def health(request):
    return JsonResponse({"status": "ok"})
