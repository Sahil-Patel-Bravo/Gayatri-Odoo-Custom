# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class AccountPayment(models.Model):
	_inherit = 'account.payment'

	def action_post(self):
		res = super().action_post()
		for rec in self:
			sale_orders = self.env['sale.order'].search([('partner_id','=',rec.partner_id.id),('state','=','draft')])
			sale_orders.onchange_on_amount_total()
		return res