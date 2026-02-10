# -*- coding: utf-8 -*-

import datetime
from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError

class PettyCashRequest(models.Model):
	_name = "petty.cash.request"
	_inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin','analytic.mixin']
	_description = "Petty Cash Request"

	name = fields.Char(string="Reference", default="New")
	request_date = fields.Datetime(string="Request Date",default=datetime.date.today())
	approve_date = fields.Datetime(string="Approve Date")
	request_amount = fields.Float(string="Request Amount", store=True)
	state = fields.Selection([('draft','Draft'),('submit','Submit'),('done','Done')],default="draft",string="Status")
	payment_journal = fields.Many2one('account.journal',string="Payment Journal",domain="['|',('type','=','cash'),('type','=','bank')]")
	company_id = fields.Many2one('res.company',string="Company",default=lambda self: self.env.company.id)
	user = fields.Many2one('res.users',string="User", default=lambda self: self.env.user.id)
	petty_cash_ref = fields.Char("Petty Cash Reference")
	from_account = fields.Many2one("account.account","Request From Account")
	to_account = fields.Many2one("account.account","Request To Account")
	journal_entry_id = fields.Many2one("account.move","Journal Entry")
	is_editable = fields.Boolean("Is Editable",compute="compute_on_editable")

	def unlink(self):
		for record in self:
			if record.state in ['submit', 'done']:
				raise UserError(_("You cannot delete records in Submit or Done state."))
		return super(PettyCashRequest, self).unlink()

	def compute_on_editable(self):
		for rec in self:
			if (self.env.user.has_group("sp_petty_cash_management.group_cash_request_approval") and self.state == "submit") or self.state == "draft":
				rec.is_editable = False
			else:
				rec.is_editable = True

	@api.model_create_multi
	def create(self, vals_list):
		"""generate cash request sequence"""
		for vals in vals_list:
			if vals.get('name', 'New') == 'New':
				vals['name'] = self.env['ir.sequence'].next_by_code('petty.cash.request') or 'New'
		result = super(PettyCashRequest, self, ).create(vals_list)
		return result

	def submit_for_approval(self):
		self.write({
			'state':'submit'
		})

	def reset_to_draft(self):
		self.write({
			'state':'draft'
		})

	def reset_to_submit(self):
		self.write({
			'state':'submit'
		})
		self.journal_entry_id.button_draft()

	def action_approve(self):
		self.action_create_petty_cash_journal_entry()
		self.write({
			'state': 'done',
		})

	def action_open_journal_entry(self):
		if self.journal_entry_id:
			return {
				'type': 'ir.actions.act_window',
				'res_model': 'account.move',
				'view_mode': 'form',
				'res_id': self.journal_entry_id.id,
			}

	def action_update_petty_cash_journal_entry(self):
		self.journal_entry_id.line_ids.unlink()
		line_ids = [(0, 0, {
					'account_id': self.to_account.id,
					'name': 'Petty Cash Sent',
					'debit': self.request_amount,
					'credit': 0.0,
				}),
				(0, 0, {
					'account_id': self.from_account.id,
					'name': 'Petty Cash Received',
					'debit': 0.0,
					'credit': self.request_amount,
				}),
		]
		self.journal_entry_id.write({'date':self.request_date,'line_ids':line_ids})
		self.journal_entry_id.action_post()
		return {
			'type': 'ir.actions.act_window',
			'res_model': 'account.move',
			'view_mode': 'form',
			'res_id': self.journal_entry_id.id,
		}

	def action_create_petty_cash_journal_entry(self):
		if not self.from_account or not self.to_account or not self.payment_journal:
			raise UserError("From Account, To Account, and Payment Journal must be set.")

		if self.request_amount <= 0:
			raise UserError("Amount must be greater than 0.")
		if self.journal_entry_id:
			self.action_update_petty_cash_journal_entry()
		else:
			move_vals = {
				'ref': f'Petty Cash Request - {self.name}',
				'journal_id': self.payment_journal.id,
				'date': self.request_date,
				'line_ids': [
					(0, 0, {
						'account_id': self.to_account.id,
						'name': 'Petty Cash Received',
						'debit': self.request_amount,
						'credit': 0.0,
					}),
					(0, 0, {
						'account_id': self.from_account.id,
						'name': 'Petty Cash Sent',
						'debit': 0.0,
						'credit': self.request_amount,
					}),
				],
			}

			move = self.env['account.move'].create(move_vals)
			move.action_post()

			self.journal_entry_id = move.id
			return {
				'type': 'ir.actions.act_window',
				'res_model': 'account.move',
				'view_mode': 'form',
				'res_id': move.id,
			}
