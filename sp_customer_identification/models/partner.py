# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
	_inherit = 'res.partner'

	sequence_id = fields.Char(
		string="Customer ID",
		help="Unique sequence identifier for the customer.",
		store=True,
		copy=False,
	)

	@api.constrains('sequence_id')
	def _check_unique_sequence_id(self):
		for rec in self:
			if not rec.sequence_id or rec.sequence_id == '/':
				continue
			duplicate = self.search([
				('sequence_id', '=', rec.sequence_id),
				('id', '!=', rec.id),
			], limit=1)
			if duplicate:
				raise ValidationError(
					_("The Customer ID '%s' already exists. Each partner must have a unique Customer ID.") % rec.sequence_id
				)

	@api.model_create_multi
	def create(self, vals_list):
		for vals in vals_list:
			seq = self.env['ir.sequence'].next_by_code('res.partner.customer.id') or '/'
			vals['sequence_id'] = seq
		return super().create(vals_list)

	@api.model
	def name_search(self, name='', args=None, operator='ilike', limit=100):
		"""
		Override name_search to allow searching customers by their name
		or customer ID (`sequence_id`).
		"""
		# Initialize the domain with arguments or an empty list
		domain = args or []
		# Add search condition for name or sequence ID
		domain = ['|', ('name', 'ilike', name), ('sequence_id', 'ilike', name)]
		# Perform the search and fetch results
		sols = self.search_fetch(domain, ['display_name'], limit=limit)
		return [(sol.id, sol.display_name) for sol in sols]

	@api.depends('sequence_id')
	def _compute_display_name(self):
		super()._compute_display_name()
		for record in self:
			if record.sequence_id:
				record.display_name = f'[{record.sequence_id}] {record.name}'
