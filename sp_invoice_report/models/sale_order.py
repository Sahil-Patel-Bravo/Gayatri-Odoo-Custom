# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class SaleOrder(models.Model):
	_inherit = "sale.order"

	po_no = fields.Char("PO NO")
	po_date = fields.Date("PO Date")
	transport = fields.Char("Transport")
	lr_no = fields.Char("LR NO")
	lr_date = fields.Date("LR Date")

	def _prepare_invoice(self):
		result = super()._prepare_invoice()
		result.update({
			"po_no":self.po_no,
			"po_date":self.po_date,
			"transport":self.transport,
			"lr_no":self.lr_no,
			"lr_date":self.lr_date,
		})
		return result
