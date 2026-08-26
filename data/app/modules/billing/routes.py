"""Route definitions for Billing Business Module."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from app.modules.billing.controllers.bank_slip_controller import BankSlipController
from app.modules.billing.controllers.invoice_controller import InvoiceController


def register_routes(router):
    """Register HTTP routes for the Billing domain package."""
    router.get("/billing/bank-slips", BankSlipController, "index")
    router.post("/billing/bank-slips", BankSlipController, "store")
    router.get("/billing/invoices", InvoiceController, "index")
    router.post("/billing/invoices", InvoiceController, "store")
