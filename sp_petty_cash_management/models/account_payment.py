# -- coding: utf-8 --

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date


class AccountPayment(models.Model):
	_inherit = "account.payment"

	is_petty_cash_request = fields.Boolean('Is Petty Cash Payment')
	is_petty_cash_expense = fields.Boolean('Is Petty Cash Expense')
	cash_request_id = fields.Many2one('petty.cash.request','Cash Request')
	cash_expense_id = fields.Many2one('petty.cash.expense','Cash Expense')

	def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
		''' Prepare the dictionary to create the default account.move.lines for the current payment.
		:param write_off_line_vals: Optional list of dictionaries to create a write-off account.move.line easily containing:
			* amount:       The amount to be added to the counterpart amount.
			* name:         The label to set on the line.
			* account_id:   The account on which create the write-off.
		:param force_balance: Optional balance.
		:return: A list of python dictionary to be passed to the account.move.line's 'create' method.
		'''
		self.ensure_one()
		write_off_line_vals = write_off_line_vals or []

		if not self.outstanding_account_id:
			raise UserError(_(
				"You can't create a new payment without an outstanding payments/receipts account set either on the company or the %(payment_method)s payment method in the %(journal)s journal.",
				payment_method=self.payment_method_line_id.name, journal=self.journal_id.display_name))

		# Compute amounts.
		write_off_line_vals_list = write_off_line_vals or []
		write_off_amount_currency = sum(x['amount_currency'] for x in write_off_line_vals_list)
		write_off_balance = sum(x['balance'] for x in write_off_line_vals_list)

		if self.payment_type == 'inbound':
			# Receive money.
			liquidity_amount_currency = self.amount
		elif self.payment_type == 'outbound':
			# Send money.
			liquidity_amount_currency = -self.amount
		else:
			liquidity_amount_currency = 0.0

		if not write_off_line_vals and force_balance is not None:
			sign = 1 if liquidity_amount_currency > 0 else -1
			liquidity_balance = sign * abs(force_balance)
		else:
			liquidity_balance = self.currency_id._convert(
				liquidity_amount_currency,
				self.company_id.currency_id,
				self.company_id,
				self.date,
			)
		counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
		counterpart_balance = -liquidity_balance - write_off_balance
		currency_id = self.currency_id.id

		# Compute a default label to set on the journal items.
		liquidity_line_name = ''.join(x[1] for x in self._get_aml_default_display_name_list() if x[1])
		counterpart_line_name = liquidity_line_name

		line_vals_list = [
			# Liquidity line.
			{
				'name': "Expense" if self.is_petty_cash_expense else liquidity_line_name,
				'date_maturity': self.date,
				'amount_currency': liquidity_amount_currency,
				'currency_id': currency_id,
				'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
				'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
				'partner_id': self.partner_id.id,
				'account_id': self.cash_expense_id.account_id.id if self.cash_expense_id else self.outstanding_account_id.id,
			},
			# Receivable / Payable.
			# {
			#     'name': counterpart_line_name,
			#     'date_maturity': self.date,
			#     'amount_currency': counterpart_amount_currency,
			#     'currency_id': currency_id,
			#     'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
			#     'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
			#     'partner_id': self.partner_id.id,
			#     'account_id': self.destination_account_id.id,
			# },
		]
		if self.is_petty_cash_expense:
			for line in self.cash_expense_id.expense_line_ids:
				line_vals_list.append(
					# Receivable / Payable.
					{
						'name': line.perticular,
						'date_maturity': self.date,
						'amount_currency': counterpart_amount_currency,
						'currency_id': currency_id,
						'debit': line.amount if line.amount > 0.0 else 0.0,
						'credit': -line.amount if line.amount < 0.0 else 0.0,
						'partner_id': self.partner_id.id,
						'account_id': line.account_id.id,
						'analytic_distribution':line.analytic_distribution,
					},
				)
		else:
			line_vals_list.append(
				# Receivable / Payable.
				{
					'name': counterpart_line_name,
					'date_maturity': self.date,
					'amount_currency': counterpart_amount_currency,
					'currency_id': currency_id,
					'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
					'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
					'partner_id': self.partner_id.id,
					'account_id': self.destination_account_id.id,
				},
			)
		return line_vals_list + write_off_line_vals_list
