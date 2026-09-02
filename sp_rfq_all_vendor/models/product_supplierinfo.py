# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    active_for_rfq = fields.Boolean(
        string="Active for RFQ",
        default=False,
        help="If ticked, this vendor line is considered when the min/max "
             "reordering workflow auto-generates RFQs. Vendors left unticked "
             "are skipped by the automatic RFQ generation only; they remain "
             "usable for manual purchase orders and price lookups.",
    )
