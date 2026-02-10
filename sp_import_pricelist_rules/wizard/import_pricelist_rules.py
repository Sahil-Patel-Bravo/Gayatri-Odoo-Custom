# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import base64
import io
import pandas as pd
from xlrd import open_workbook
from base64 import b64decode
try:
	from xlrd import open_workbook
except ImportError:
	_logger.debug("Can not import xlrd`.")

class ImportPricelistRules(models.TransientModel):
	_name = "import.pricelist.rules"
	_description = "Import Pricelist Rules"

	name = fields.Char("Pricelist Name")
	file = fields.Binary("File")

	def action_import(self):
		try:
			# book = open_workbook(file_contents=base64.decodebytes(self.file))
			# book = xlrd.open_workbook(file_contents=b64decode(self.file) or b'')
			book = open_workbook(file_contents=b64decode(self.file))
			sheet = book.sheet_by_index(0)
			sheet.row_slice
			TotalCol = len(sheet.col(0))
			rows = 0
		except Exception as e:
			raise Warning(_(e))
		dict_index = 0
		lines = []
		item_ids = []
		for i in range(1,TotalCol):
			col1 = sheet.cell_value(i,0) if sheet.cell_value(i,0) else ""
			col2 = sheet.cell_value(i,1) if sheet.cell_value(i,1) else ""
			col3 = sheet.cell_value(i,2) if sheet.cell_value(i,2) else ""
			col4 = sheet.cell_value(i,3) if sheet.cell_value(i,3) else ""
			col5 = sheet.cell_value(i,4) if sheet.cell_value(i,4) else ""
			if col2:
				if isinstance(col2, float):
					col2 = str(int(col2))
				else:
					col2 = str(col2).strip()
			if col3:
				col3 = str(col3).strip()
			product_id = self.env['product.product'].search([('default_code','=',col2),('name','=',col3)])
			item_ids.append((0,0,{
				"name":col1,
				"product_id":product_id.id,
				"product_tmpl_id":product_id.product_tmpl_id.id,
				"compute_price":col4,
				"percent_price":float(col5),
			}))
		vals = {
			"name":self.name,
			"item_ids": item_ids
		}
		self.env['product.pricelist'].create(vals)