# -*- coding: utf-8 -*-

import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PettyCashExpense(models.Model):
	_name = "petty.cash.expense"
	_inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin','analytic.mixin']
	_description = "Petty Cash Expense"

	name = fields.Char(string="Reference", default="New",copy=True)
	state = fields.Selection([('draft','Draft'),('confirm','Confirm'),('done','Done'),('cancel','Cancel')],default="draft",string="Status")
	employee_id = fields.Many2one('hr.employee',string="Employee",required=False)
	payment_journal_id = fields.Many2one('account.journal',string="Payment journal",domain="['|', ('type', '=', 'cash'), ('type', '=', 'bank')]")
	cash_journal_id =fields.Many2one('account.journal',string="Cash Journal")
	user_id = fields.Many2one('res.users',string="Responsible User ",default=lambda self: self.env.user.id)
	company_id = fields.Many2one('res.company',string="Company",default=lambda self: self.env.company.id)
	expense_line_ids = fields.One2many('petty.cash.expense.lines','expense_id',string="Expense Lines")
	currency_id = fields.Many2one('res.currency', string="Currency",related='company_id.currency_id',)
	expense_amount = fields.Monetary(string="Total Amount", compute="_compute_expense_amount")
	payment_id = fields.Many2one('account.payment',string="Payment")
	account_id = fields.Many2one('account.account',string="To Account")
	analytic_distribution = fields.Json(string="Analytic Distribution")
	date = fields.Date("Date")

	def unlink(self):
		for record in self:
			if record.state in ['done']:
				raise UserError(_("You cannot delete records in Done state."))
		return super(PettyCashExpense, self).unlink()

	@api.depends('expense_line_ids')
	def _compute_expense_amount(self):
		for rec in self:
			amt = 0
			for line in rec.expense_line_ids:
				amt += line.amount
			rec.expense_amount = amt

	@api.model_create_multi
	def create(self, vals_list):
		"""generate cash expense sequence"""
		for vals in vals_list:
			if vals.get('name', 'New') == 'New':
				vals['name'] = self.env['ir.sequence'].next_by_code('petty.cash.expense') or 'New'
		result = super(PettyCashExpense, self, ).create(vals_list)
		return result

	def action_confirm(self):
		# if not self.employee_id.bank_account_id:
			# raise UserError(_("Please add bank account for %s",self.employee_id.name))
		# if not self.employee_id.bank_account_id.partner_id:
			# raise UserError(_("Partner is not set for %s bank account", self.employee_id.name))
		if not self.expense_line_ids:
			raise UserError(_("Please add expense line"))

		self.write({
			'state':'confirm'
		})

	def action_reconcile_payment(self):
		vals = {
			'payment_type':'outbound',
			# 'partner_id':self.employee_id.user_partner_id.id,
			'amount':self.expense_amount,
			'date':self.date,
			'journal_id':self.payment_journal_id.id,
			# 'partner_id':self.employee_id.address_id.id,
			'is_petty_cash_expense':True,
			'cash_expense_id':self.id,
		}
		skip_context = {
			'skip_invoice_sync': True,
			'skip_invoice_line_sync': True,
			'skip_account_move_synchronization': True,
			'check_move_validity': False,
		}
		payment_id = self.env['account.payment'].with_context(**skip_context).create(vals)
		payment_id.action_post()
		self.write({
			'state': 'done',
			'payment_id':payment_id.id
		})

	def action_cancel(self):
		self.write({
			'state': 'cancel',
		})

	def action_open_payment(self):
		if self.payment_id:
			payment_id = self.env['account.payment'].search([('id','=',self.payment_id.id)]).id
			return {
				'type': 'ir.actions.act_window',
				'view_mode': 'form',
				'res_model': 'account.payment',
				'views': [(False, 'form')],
				'res_id': payment_id,
			}


class PettyCashExpenseLines(models.Model):
	_name = "petty.cash.expense.lines"
	_inherit = ['analytic.mixin']
	_description = "Petty Cash Expense Lines"

	expense_id = fields.Many2one('petty.cash.expense')
	perticular = fields.Char('Particulars')
	account_id = fields.Many2one('account.account',string="Account")
	company_id = fields.Many2one('res.company', string="Company")
	currency_id = fields.Many2one('res.currency', string="Currency",related='company_id.currency_id')
	vehicle = fields.Many2one("fleet.vehicle","Vehicle")
	amount = fields.Monetary(string="Amount", store=True)
	analytic_distribution = fields.Json(string="Analytic Distribution",related="expense_id.analytic_distribution")
