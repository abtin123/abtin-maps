from django.contrib import admin
from .models import Customer, PriceLevel, ProductPrice, Campaign, Invoice, InvoiceItem, InvoiceStatusHistory, ApprovalRequest, Payment
for model in (Customer, PriceLevel, ProductPrice, Campaign, Invoice, InvoiceItem, InvoiceStatusHistory, ApprovalRequest, Payment):
    admin.site.register(model)
