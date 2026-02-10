# -- coding: utf-8 --

{
	'name': 'Sale Sequence',
	'version': '1.0',
	'author': 'SP Technologies Solution',
	'summary': 'Module for Sale Sequence',
	'description': """Sale Delivery and Invoice Status in Odoo""",
	'category': 'Sale',
	'website': 'https://sptechnologiessolution.com/',
	'depends': ['base','sale'],
	'data': [
		'data/sequence.xml',
		'views/sale_order_view.xml',
	],
	'qweb': [],
	"license": 'LGPL-3',
	'images': ['static/description/icon.png'],
	'installable': True,
	'application': True,
	'auto_install': False,
	"maintainers": ['SP'],
}
