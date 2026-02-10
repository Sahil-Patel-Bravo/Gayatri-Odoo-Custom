# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class ResPartner(models.Model):
	_inherit = 'res.partner'

	payment_type = fields.Selection([('credit','Credit'),('advance','Advance Payment')],string="Payment Type",default="advance")
	credit_limit_amount = fields.Float("Credit Limit ")

	def get_advance_amount(self):
		payment_ids = self.env['account.payment'].search([('payment_type','=','inbound'),('state','=','in_process'),('partner_id','=',self.id)])
		reconciled_invoice_ids = payment_ids.reconciled_invoice_ids
		amount_total = sum(reconciled_invoice_ids.mapped('amount_total'))
		payment_amount = sum(payment_ids.mapped('amount'))
		advance_amount = payment_amount - amount_total
		return advance_amount