# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SaleOrderLine(models.Model):
	_inherit = "sale.order.line"

	def action_sale_history(self):
		self.ensure_one()
		action = self.env["ir.actions.actions"]._for_xml_id("sp_last_sale_price_history.action_sale_history")
		action['domain'] = [('state', 'in', ['sale', 'done']), ('product_id', '=', self.product_id.id)]
		action['display_name'] = _("Sale History for %s", self.product_id.display_name)
		action['context'] = {}

		return action
