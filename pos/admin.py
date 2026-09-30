from django.contrib import admin
from .models import (
    StaffProfile, Supplier, Product, Sale, SaleItem,
    ProductReturn, LedgerEntry
)

admin.site.register(StaffProfile)
admin.site.register(Supplier)
admin.site.register(Product)
admin.site.register(Sale)
admin.site.register(SaleItem)
admin.site.register(ProductReturn)
admin.site.register(LedgerEntry)
