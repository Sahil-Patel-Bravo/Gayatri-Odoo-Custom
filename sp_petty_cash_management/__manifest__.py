# -- coding: utf-8 --

{
	'name': 'SP Petty Cash Management',
	'version': '1.0',
	'author': 'SP Technologies Solution',
	'summary': 'Petty Cash Management',
	'description': """Petty Cash Management""",
	'category': 'Accounting',
	'website': 'https://sptechnologiessolution.com/',
	'depends': ['base','account_accountant','hr','fleet'],
	'data': [
		'security/ir.model.access.csv',
		'security/security.xml',
		'data/sequence.xml',
		'views/cash_request_view.xml',
		'views/cash_expense_view.xml',
		'views/menus_view.xml',
	],
	'qweb': [],
	"license": 'LGPL-3',
	'images': ['static/description/icon.png'],
	'installable': True,
	'application': True,
	'auto_install': False,
	"maintainers": ['SP'],
}
