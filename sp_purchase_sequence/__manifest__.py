# -- coding: utf-8 --

{
	'name': 'Purchase Sequence',
	'version': '1.0',
	'author': 'SP Technologies Solution',
	'summary': 'Purchase Sequence',
	'description': """
		Purchase Sequence
		========================
		This module provides features to manage Purchase Sequence
	""",
	'category': 'Purchase',
	'website': 'https://sptechnologiessolution.com/',
	'depends': ['base','purchase'],
	'data': [
		'data/sequence.xml',
		'views/purchase_order_view.xml',
	],
	'qweb': [],
	"license": 'LGPL-3',
	'images': ['static/description/icon.png'],
	'installable': True,
	'application': True,
	'auto_install': False,
	"maintainers": ['SP'],
}
