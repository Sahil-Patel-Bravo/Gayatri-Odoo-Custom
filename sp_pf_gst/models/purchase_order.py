# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class PurchaserderLine(models.Model):
	_inherit = 'purchase.order.line'

	pf_gst_per = fields.Float("P&F Percentage")
	pf_gst_amount = fields.Float("P&F Amount",compute="compute_on_pf")
	is_hilti = fields.Boolean()

	@api.onchange('product_id')
	def onchange_product_pf_gst(self):
		if self.product_id:
			self.pf_gst_per = self.product_id.pf_gst
			self.is_hilti = self.product_id.is_hilti
			
	@api.depends("pf_gst_per", "tax_ids", "price_unit", "product_qty", "discount")
	def compute_on_pf(self):
		for rec in self:
			price_subtotal = rec.price_unit * rec.product_qty
			discount = rec.order_id.currency_id.round(price_subtotal * rec.discount / 100)
			price_subtotal -= discount
			rec.pf_gst_amount = rec.order_id.currency_id.round(price_subtotal * rec.pf_gst_per / 100)

	@api.depends('product_qty', 'price_unit', 'tax_ids', 'discount')
	def _compute_amount(self):
		for line in self:
			base_line = line._prepare_base_line_for_taxes_computation()
			self.env['account.tax']._add_tax_details_in_base_line(base_line, line.company_id)
			price_subtotal = line.price_unit * line.product_qty
			discount = line.order_id.currency_id.round(price_subtotal * line.discount / 100)
			price_subtotal -= discount
			pf_gst_amount = line.order_id.currency_id.round(price_subtotal * line.pf_gst_per / 100)
			line.price_subtotal = line.order_id.currency_id.round(base_line['tax_details']['raw_total_excluded_currency'] + pf_gst_amount)
			line.price_total = line.order_id.currency_id.round(base_line['tax_details']['raw_total_included_currency'])
			line.price_tax = line.price_total - line.price_subtotal

	def _prepare_account_move_line(self, move=False):
		res = super()._prepare_account_move_line(move)
		res.update({
			"pf_gst_per": self.pf_gst_per,
			"pf_gst_amount": self.order_id.currency_id.round(self.pf_gst_amount),
		})
		return res

class PurchaseOrder(models.Model):
	_inherit = 'purchase.order'

	def get_pf_name(self):
		for rec in self:
			names_set = set(rec.order_line.mapped('pf_gst_per'))
			names_list = [str(name) for name in names_set]
			if names_list:
				name = ",".join(names_list)
				return name

	def get_total_gst(self):
		for rec in self:
			total_gst = sum(rec.order_line.mapped("pf_gst_amount"))
			total_tax = rec.get_total_tax_on_gst()
			return total_gst

	def get_total_tax_on_gst(self,tax_id=False):
		for rec in self:
			tax_amount = 0
			for line in rec.order_line:
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

	@api.depends('order_line.price_subtotal', 'currency_id', 'company_id', 'order_line.pf_gst_per')
	def _amount_all(self):
		AccountTax = self.env['account.tax']
		for order in self:
			order_lines = order.order_line.filtered(lambda x: not x.display_type)
			base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
			AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
			AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
			tax_totals = AccountTax._get_tax_totals_summary(
				base_lines=base_lines,
				currency=order.currency_id or order.company_id.currency_id,
				company=order.company_id,
			)
			gst_amount = order.currency_id.round(sum(order.order_line.mapped('pf_gst_amount')))
			gst_amount_line = order.currency_id.round(order.get_total_tax_on_gst())
			
			order.amount_untaxed = order.currency_id.round(tax_totals['base_amount_currency'] + gst_amount)
			order.amount_tax = order.currency_id.round(tax_totals['tax_amount_currency'] + gst_amount_line)
			order.amount_total = order.currency_id.round(tax_totals['total_amount_currency'] + gst_amount + gst_amount_line)
			order.amount_total_cc = order.currency_id.round(tax_totals['total_amount'] + gst_amount + gst_amount_line)

	@api.depends_context('lang')
	@api.depends('order_line.price_subtotal', 'currency_id', 'company_id','order_line.pf_gst_per')
	def _compute_tax_totals(self):
		AccountTax = self.env['account.tax']
		for order in self:
			if not order.company_id:
				order.tax_totals = False
				continue
			order_lines = order.order_line.filtered(lambda x: not x.display_type)
			base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
			AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
			AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
			order.tax_totals = AccountTax._get_tax_totals_summary(
				base_lines=base_lines,
				currency=order.currency_id or order.company_id.currency_id,
				company=order.company_id,
			)
			gst_amount = sum(order.order_line.mapped('pf_gst_amount'))
			gst_amount_line = order.get_total_tax_on_gst()
			for subtotal in order.tax_totals['subtotals']:
				if subtotal['name'] == 'Untaxed Amount':
					subtotal['base_amount'] = subtotal['base_amount'] + gst_amount
					subtotal['base_amount_currency'] = subtotal['base_amount_currency'] + gst_amount
				if subtotal.get('tax_groups'):
					for tax_group in subtotal['tax_groups']:
						line_gst_amount_line = order.get_total_tax_on_gst(tax_id=tax_group.get('id'))
						tax_group['tax_amount'] = tax_group['tax_amount'] + line_gst_amount_line
						tax_group['tax_amount_currency'] = tax_group['tax_amount_currency'] + line_gst_amount_line

			order.tax_totals['base_amount_currency'] = order.tax_totals['base_amount_currency'] + gst_amount + gst_amount_line
			order.tax_totals['total_amount_currency'] = order.tax_totals['total_amount_currency'] + gst_amount + gst_amount_line
			order.tax_totals['base_amount'] = order.tax_totals['base_amount'] + gst_amount + gst_amount_line
			order.tax_totals['total_amount'] = order.tax_totals['total_amount'] + gst_amount + gst_amount_line
