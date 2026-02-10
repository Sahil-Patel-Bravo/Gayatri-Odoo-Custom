# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
	_inherit = 'sale.order'

	rfq_seq = fields.Char("RFQ Sequence")

	@api.model_create_multi
	def create(self,vals_list):
		orders = self.browse()
		for vals in vals_list:
			sequence = self.env['ir.sequence'].next_by_code('quotation.order') or '/'
			vals['name'] = sequence
			orders |= super(SaleOrder, self).create(vals)
		return orders

	def action_confirm(self):
		res = super().action_confirm()
		self.rfq_seq = self.name
		if self.date_order:
			seq_date = fields.Datetime.context_timestamp(self, self.date_order)
			self.name = self.env['ir.sequence'].next_by_code('sale.order', sequence_date=seq_date) or '/'
		for picking_id in self.picking_ids:
			picking_id.origin = picking_id.origin + ',' + self.name
		return res