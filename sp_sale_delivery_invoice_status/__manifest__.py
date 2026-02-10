# -- coding: utf-8 --

{
	'name': 'Sale Delivery and Invoice Status in Odoo',
	'version': '1.0',
	'author': 'SP Technologies Solution',
	'summary': 'Sale Delivery and Invoice Status in Odoo',
	'description': """Sale Delivery and Invoice Status in Odoo""",
	'category': 'Sales Management',
	'website': 'https://sptechnologiessolution.com/',
	'depends': ['base','sale_management','sale_stock'],
	'data': [
		'views/main_delivery_invoice.xml',
	],
	'qweb': [],
	"license": 'LGPL-3',
	'images': ['static/description/icon.png'],
	'installable': True,
	'application': True,
	'auto_install': False,
	"maintainers": ['SP'],
}
