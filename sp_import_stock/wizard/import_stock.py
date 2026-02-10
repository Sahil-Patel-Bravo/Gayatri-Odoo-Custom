# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import base64
import io
import pandas as pd
from xlrd import open_workbook

class ImportStock(models.TransientModel):
	_name = "import.stock"
	_description = "Import Stock"

	file = fields.Binary("File")

	def action_import(self):
		try:
			book = open_workbook(file_contents=base64.decodebytes(self.file))
			sheet = book.sheet_by_index(0)
			sheet.row_slice
			TotalCol = len(sheet.col(0))
			rows = 0
		except Exception as e:
			raise Warning(_(e))
		dict_index = 0
		lines = []
		for i in range(1,TotalCol):
			col1 = sheet.cell_value(i,0) if sheet.cell_value(i,0) else ""
			col2 = sheet.cell_value(i,1) if sheet.cell_value(i,1) else ""
			col3 = sheet.cell_value(i,2) if sheet.cell_value(i,2) else ""
			col4 = sheet.cell_value(i,3) if sheet.cell_value(i,3) else ""
			if col1:
				if isinstance(col1, float):
					col1 = str(int(col1))
				else:
					col1 = str(col1).strip()
			product_id = self.env['product.product'].search(['|',('default_code','=',col1),('name','=',col2)],limit=1)
			location_id = self.env['stock.location'].search([('display_name','=',col3)],limit=1)
			vals = {
					"product_id":product_id.id,
					"location_id":location_id.id,
					"quantity":col4,
				}
			self.env['stock.quant'].create(vals)