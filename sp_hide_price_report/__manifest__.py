# -- coding: utf-8 --

{
	'name': 'Hide Price on Report',
	'version': '1.0',
	'author': 'SP Technologies Solution',
	'summary': 'Hide Price on Report',
	'description': """Hide Price on Report""",
	'category': 'Reports',
	'website': 'https://sptechnologiessolution.com/',
	'depends': ['base','sale','account'],
	'data': [
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
