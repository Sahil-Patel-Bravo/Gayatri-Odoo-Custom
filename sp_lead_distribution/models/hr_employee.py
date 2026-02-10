# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class HrEmployee(models.Model):
	_inherit = 'hr.employee'

	zip_distribute = fields.One2many(
		"zip.distribute.line",
		"employee_id",
		string="Zip/State Distribution",
		help="Defines the zip and state distribution for the employee."
	)


class ZipDistributeLine(models.Model):
	_name = 'zip.distribute.line'
	_description = 'Zip Distribute Line'

	employee_id = fields.Many2one(
		"hr.employee",
		string="Employee",
		help="The employee associated with this zip/state distribution line."
	)
	state_id = fields.Many2one(
		"res.country.state",
		string="State",
		help="The state associated with this distribution line."
	)
	zip = fields.Char(
		string="Zip",
		help="The zip code associated with this distribution line."
	)
	state_zip_dict = fields.Char(
		string="State Zip Dict",
		help="Stores a combination of state and zip as a dictionary format."
	)
	state_dict = fields.Char(
		string="State Dict",
		help="Stores a combination of state and zip as a dictionary format."
	)

	@api.onchange("zip", "state_id")
	def onchange_on_state_zip_dict(self):
		"""
		Updates `state_zip_dict` field whenever `zip` or `state_id` changes.
		Combines `zip` and `state_id` into a formatted string.
		"""
		for rec in self:
			rec.state_zip_dict = "[%s, %s]" % (rec.zip, rec.state_id.id)
			if not rec.zip:
				rec.state_dict = "[%s]" % (rec.state_id.id)
			else:
				rec.state_dict = ""