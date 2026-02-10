# -- coding: utf-8 --

{
	'name': 'Invoice Report Enhancement',
	'version': '1.0',
	'author': 'SP Technologies Solution',
	'summary': 'Invoice Report Enhancement',
	'description': """Invoice Report Enhancement""",
	'category': 'Reports',
	'website': 'https://sptechnologiessolution.com/',
	'depends': ['base','sale','account','l10n_in'],
	'data': [
		'views/account_move_view.xml',
		'views/sale_order_view.xml',
		'report/report_template.xml',
	],
	'qweb': [],
	"license": 'LGPL-3',
	'images': ['static/description/icon.png'],
	'installable': True,
	'application': True,
	'auto_install': False,
	"maintainers": ['SP'],
}
