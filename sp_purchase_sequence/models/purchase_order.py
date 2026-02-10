# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
	_inherit = 'purchase.order'

	rfq_seq = fields.Char("RFQ Sequence")

	@api.model_create_multi
	def create(self,vals_list):
		orders = super().create(vals_list)
		for order in orders:
			# rfq_orders = self.env['purchase.order'].search([('state','=','draft')])
			# total_rfq = len(rfq_orders) + 1
			# next_rfq_seq = str(total_rfq).zfill(5)
			# sequence = "RFQ%s" % (str(next_rfq_seq))
			sequence = self.env['ir.sequence'].next_by_code('rfq.order') or '/'
			order.name = sequence
		return orders

	def button_confirm(self):
		res = super().button_confirm()
		self.rfq_seq = self.name
		if self.date_order:
			seq_date = fields.Datetime.context_timestamp(self, self.date_order)
			self.name = self.env['ir.sequence'].next_by_code('purchase.order', sequence_date=seq_date) or '/'
		for picking_id in self.picking_ids:
			picking_id.origin = picking_id.origin + ',' + self.name
		return res