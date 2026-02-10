# -- coding: utf-8 --

from odoo import models, fields, api, _


class HrEmployee(models.Model):
	_inherit = "hr.employee"

	petty_cash_balance = fields.Float("Petty Cash Balance",compute="compute_on_petty_cash_balance")

	def compute_on_petty_cash_balance(self):
		for rec in self:
			cash_request_ids = self.env['petty.cash.request'].search([('request_by_id','=',rec.id),('state','=','done')])
			expense_request_ids = self.env['petty.cash.expense'].search([('employee_id','=',rec.id),('state','=','done')])
			balance = sum(cash_request_ids.mapped("request_amount"))
			expense_amount = sum(expense_request_ids.mapped("expense_amount"))
			balance -= expense_amount
			rec.petty_cash_balance = balance
