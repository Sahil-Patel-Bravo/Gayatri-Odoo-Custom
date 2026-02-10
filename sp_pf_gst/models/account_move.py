# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class AccountMoveLine(models.Model):
	_inherit = 'account.move.line'

	pf_gst_per = fields.Float("P&F Percentage")
	pf_gst_amount = fields.Float("P&F Amount",compute="compute_on_pf")
	is_hilti = fields.Boolean()
	is_pf_line = fields.Boolean("Is PF Line")
	display_type = fields.Selection(selection_add=[('gst_charge','GST Charge')],ondelete={'gst_charge': 'cascade'})

	@api.onchange('product_id')
	def onchange_product_pf_gst(self):
		if self.product_id:
			self.pf_gst_per = self.product_id.pf_gst 
			self.is_hilti = self.product_id.is_hilti 
			
	@api.depends("pf_gst_per","tax_ids","price_unit","quantity")
	def compute_on_pf(self):
		for rec in self:
			price_subtotal = rec.price_unit * rec.quantity
			discount = rec.currency_id.round(price_subtotal * rec.discount / 100)
			price_subtotal -= discount 
			rec.pf_gst_amount = rec.currency_id.round(price_subtotal * rec.pf_gst_per / 100)

	@api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id')
	def _compute_totals(self):
		""" Compute 'price_subtotal' / 'price_total' outside of `_sync_tax_lines` because those values must be visible for the
		user on the UI with draft moves and the dynamic lines are synchronized only when saving the record.
		"""
		AccountTax = self.env['account.tax']
		for line in self:
			# TODO remove the need of cogs lines to have a price_subtotal/price_total
			if line.display_type not in ('product', 'cogs'):
				line.price_total = line.price_subtotal = False
				continue

			base_line = line.move_id._prepare_product_base_line_for_taxes_computation(line)
			AccountTax._add_tax_details_in_base_line(base_line, line.company_id)
			line.price_subtotal = base_line['tax_details']['raw_total_excluded_currency'] + line.pf_gst_amount
			line.price_total = base_line['tax_details']['raw_total_included_currency']

	def create(self,vals):
		res = super().create(vals)
		if not self._context.get('one_time'):
			res.move_id._add_gst_charge_line()
		return res

	def write(self,vals):
		res = super().write(vals)
		if not self._context.get('one_time'):
			self.move_id._add_gst_charge_line()
		return res

class AccountMove(models.Model):
	_inherit = 'account.move'

	def create(self,vals):
		res = super().create(vals)
		if not self._context.get('one_time'):
			res._add_gst_charge_line()
		return res

	def write(self,vals):
		res = super().write(vals)
		if not self._context.get('one_time'):
			self._add_gst_charge_line()
		return res

	def get_pf_name(self):
		for rec in self:
			names_set = set(rec.invoice_line_ids.mapped('pf_gst_per'))
			names_list = [str(name) for name in names_set]
			if names_list:
				name = ",".join(names_list)
				return name

	def get_total_gst(self):
		for rec in self:
			total_gst = sum(rec.invoice_line_ids.mapped("pf_gst_amount"))
			total_tax = rec.get_total_tax_on_gst()
			return total_gst

	def get_total_tax_on_gst(self,tax_id=False):
		for rec in self:
			tax_amount = 0
			for line in rec.invoice_line_ids:
				line_tax_amount = 0
				tax_ids = line.tax_ids
				for tax in tax_ids:
					if tax_id:
						if tax.amount_type == "group":
							for child_tax in tax.children_tax_ids:
								if child_tax.tax_group_id.id == tax_id:
									tax_rate = child_tax.amount
									child_line_tax_amount = line.pf_gst_amount * tax_rate / 100
									line_tax_amount += child_line_tax_amount
						else:
							if tax.tax_group_id.id == tax_id:
								tax_rate = tax.amount
								tax_line_tax_amount = line.pf_gst_amount * tax_rate / 100
								line_tax_amount += tax_line_tax_amount
					else:
						if tax.amount_type == "group":
							for child_tax in tax.children_tax_ids:
								tax_rate = child_tax.amount
								child_line_tax_amount = line.pf_gst_amount * tax_rate / 100
								line_tax_amount += child_line_tax_amount
						else:
							tax_rate = tax.amount
							tax_line_tax_amount = line.pf_gst_amount * tax_rate / 100
							line_tax_amount += tax_line_tax_amount
				tax_amount += line_tax_amount
			return tax_amount

	def _add_gst_charge_line(self):
		for record in self:
			if record.state == "draft" and record.move_type in ("out_invoice", "in_invoice", "out_refund", "in_refund"):
				invoice_line_ids = record.line_ids.filtered(lambda line: line.display_type == "gst_charge")
				gst_total = sum(record.invoice_line_ids.mapped('pf_gst_amount'))
				gst_amount_line = record.get_total_tax_on_gst()
				total_amount = gst_total + gst_amount_line
				
				if record.move_type in ("out_invoice", "in_refund"):
					final_balance = -abs(total_amount)
				else:
					final_balance = abs(total_amount)

				if invoice_line_ids:
					invoice_line_ids.with_context(one_time=True).write({'balance': final_balance})
				else:
					record.with_context(one_time=True).write({
						'line_ids': [(0, 0, {
							'name': 'GST Charges',
							'quantity': 1,
							'display_type': 'gst_charge',
							'price_unit': abs(total_amount),
							'balance': final_balance,
							'account_id': record.journal_id.default_account_id.id,
						})]
					})

	@api.depends(
		'line_ids.matched_debit_ids.debit_move_id.move_id.origin_payment_id.is_matched',
		'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
		'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
		'line_ids.matched_credit_ids.credit_move_id.move_id.origin_payment_id.is_matched',
		'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
		'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
		'line_ids.balance',
		'line_ids.currency_id',
		'line_ids.amount_currency',
		'line_ids.amount_residual',
		'line_ids.amount_residual_currency',
		'line_ids.payment_id.state',
		'line_ids.full_reconcile_id',
		'state')
	def _compute_amount(self):
		for move in self:
			total_untaxed, total_untaxed_currency = 0.0, 0.0
			total_tax, total_tax_currency = 0.0, 0.0
			total_residual, total_residual_currency = 0.0, 0.0
			total, total_currency = 0.0, 0.0

			for line in move.line_ids:
				if move.is_invoice(True):
					# === Invoices ===
					if line.display_type == 'tax' or (line.display_type == 'rounding' and line.tax_repartition_line_id):
						# Tax amount.
						total_tax += line.balance
						total_tax_currency += line.amount_currency
						total += line.balance
						total_currency += line.amount_currency
					elif line.display_type in ('product', 'rounding'):
						# Untaxed amount.
						total_untaxed += line.balance
						total_untaxed_currency += line.amount_currency
						total += line.balance
						total_currency += line.amount_currency
					elif line.display_type == 'payment_term':
						# Residual amount.
						total_residual += line.amount_residual
						total_residual_currency += line.amount_residual_currency
				else:
					# === Miscellaneous journal entry ===
					if line.debit:
						total += line.balance
						total_currency += line.amount_currency

			sign = move.direction_sign
			gst_amount = sum(move.invoice_line_ids.mapped('pf_gst_amount'))
			gst_amount_line = move.get_total_tax_on_gst()
			amount_untaxed = sign * total_untaxed_currency
			move.amount_untaxed = amount_untaxed + gst_amount
			move.amount_tax = sign * total_tax_currency + gst_amount_line
			amount_total = sign * total_currency
			move.amount_total = amount_total + gst_amount + gst_amount_line
			move.amount_residual = -sign * total_residual_currency
			move.amount_untaxed_signed = -total_untaxed
			move.amount_untaxed_in_currency_signed = -total_untaxed_currency
			move.amount_tax_signed = -total_tax
			move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
			move.amount_residual_signed = total_residual
			move.amount_total_in_currency_signed = abs(move.amount_total) if move.move_type == 'entry' else -(sign * move.amount_total)

	@api.depends_context('lang')
	@api.depends(
		'invoice_line_ids.currency_rate',
		'invoice_line_ids.tax_base_amount',
		'invoice_line_ids.tax_line_id',
		'invoice_line_ids.price_total',
		'invoice_line_ids.price_subtotal',
		'invoice_payment_term_id',
		'partner_id',
		'currency_id',
	)
	def _compute_tax_totals(self):
		""" Computed field used for custom widget's rendering.
			Only set on invoices.
		"""
		for move in self:
			if move.is_invoice(include_receipts=True):
				base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()
				move.tax_totals = self.env['account.tax']._get_tax_totals_summary(
					base_lines=base_lines,
					currency=move.currency_id,
					company=move.company_id,
					cash_rounding=move.invoice_cash_rounding_id,
				)
				move.tax_totals['display_in_company_currency'] = (
					move.company_id.display_invoice_tax_company_currency
					and move.company_currency_id != move.currency_id
					and move.tax_totals['has_tax_groups']
					and move.is_sale_document(include_receipts=True)
				)
				gst_amount = move.currency_id.round(sum(move.invoice_line_ids.mapped('pf_gst_amount')))
				gst_amount_line = move.currency_id.round(move.get_total_tax_on_gst())
				for subtotal in move.tax_totals['subtotals']:
					if subtotal['name'] == 'Untaxed Amount':
						subtotal['base_amount'] = subtotal['base_amount']
						subtotal['base_amount_currency'] = subtotal['base_amount_currency'] + gst_amount
					if subtotal.get('tax_groups'):
						for tax_group in subtotal['tax_groups']:
							line_gst_amount_line = move.get_total_tax_on_gst(tax_id=tax_group.get('id'))
							tax_group['tax_amount'] = tax_group['tax_amount'] + line_gst_amount_line if move.move_type in ("out_invoice","out_refund") else tax_group['tax_amount']
							# tax_group['tax_amount_currency'] = tax_group['tax_amount_currency'] + line_gst_amount_line if move.move_type == "out_invoice" else tax_group['tax_amount_currency']
							tax_group['tax_amount_currency'] = tax_group['tax_amount_currency'] + line_gst_amount_line
				
				move.tax_totals['base_amount_currency'] = move.tax_totals['base_amount_currency'] + gst_amount + gst_amount_line
				move.tax_totals['total_amount_currency'] = move.tax_totals['total_amount_currency'] + gst_amount + gst_amount_line
				move.tax_totals['base_amount'] = move.tax_totals['base_amount'] 
				move.tax_totals['total_amount'] = move.tax_totals['total_amount'] + gst_amount + gst_amount_line
			else:
				# Non-invoice moves don't support that field (because of multicurrency: all lines of the invoice share the same currency)
				move.tax_totals = None
