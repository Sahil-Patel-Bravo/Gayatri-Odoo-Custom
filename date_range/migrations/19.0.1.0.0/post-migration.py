# Copyright 2026 ACSONE SA/NV (<http://acsone.eu>)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    """Migration script for Odoo 19.0"""
    # No specific migrations needed for 19.0 at this time
    # This script is kept for future migrations if needed
    pass
