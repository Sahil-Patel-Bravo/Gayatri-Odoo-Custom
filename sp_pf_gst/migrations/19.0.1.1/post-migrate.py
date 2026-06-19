# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """On upgrade, patch GSTR1/2B/3B formulas and backfill gst_charge sections
    so the P&F (gst_charge) lines are picked up by the GST reports.

    Reuses the same logic as the install-time post_init_hook.
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.sp_pf_gst.hooks import _patch_gst_report_formulas
    _patch_gst_report_formulas(env)
