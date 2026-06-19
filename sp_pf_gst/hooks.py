# -*- coding: utf-8 -*-

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Ensure gst_charge sections and GST report formulas are set up correctly.

    1. Backfill l10n_in_gstr_section on P&F base gst_charge lines.
    2. Clear GSTR section on P&F tax gst_charge lines.
    3. Patch GSTR1, GSTR-2B, and GSTR-3B domain formulas.

    NOTE: migrating old combined 'GST Charges' lines into the new split
    structure is handled by the *Migrate P&F GST Lines* server action (run
    manually), NOT here — it must never auto-run on install/upgrade.
    """
    _patch_gst_report_formulas(env)


def _patch_gst_report_formulas(env):
    # --- Backfill GSTR section on P&F base gst_charge lines ---
    gst_charge_lines = env['account.move.line'].search([
        ('display_type', '=', 'gst_charge'),
        ('name', 'in', ['P&F Charges', 'GST Charges']),
        ('move_id.state', '=', 'posted'),
    ])
    for line in gst_charge_lines:
        product_section = line.move_id.line_ids.filtered(
            lambda l: l.display_type == 'product'
            and l.l10n_in_gstr_section
            and l.l10n_in_gstr_section not in (False, 'sale_out_of_scope', 'purchase_out_of_scope')
        )[:1].l10n_in_gstr_section
        if product_section:
            line.l10n_in_gstr_section = product_section

    # --- 3. Ensure P&F tax lines do NOT have a GSTR section ---
    pf_tax_lines = env['account.move.line'].search([
        ('display_type', '=', 'gst_charge'),
        ('name', 'not in', ['P&F Charges', 'GST Charges']),
        ('l10n_in_gstr_section', '!=', False),
    ])
    if pf_tax_lines:
        pf_tax_lines.write({'l10n_in_gstr_section': False})

    # --- 4. Patch GSTR1, GSTR-2B, GSTR-3B formulas ---
    report_refs = [
        'l10n_in_reports.account_report_gstr1',
        'l10n_in_reports.account_report_gstr2b',
        'l10n_in_reports.account_report_gstr3b',
    ]
    report_ids = []
    for ref in report_refs:
        report = env.ref(ref, raise_if_not_found=False)
        if report:
            report_ids.append(report.id)

    if not report_ids:
        return

    exprs = env['account.report.expression'].search([
        ('report_line_id.report_id', 'in', report_ids),
        ('engine', '=', 'domain'),
        ('formula', 'like', 'display_type'),
        ('formula', 'not like', 'gst_charge'),
    ])
    patched = 0
    for expr in exprs:
        new_formula = expr.formula.replace(
            "('display_type', '=', 'product')",
            "('display_type', 'in', ['product', 'gst_charge'])",
        )
        if new_formula != expr.formula:
            expr.formula = new_formula
            patched += 1

    _logger.info("Patched %d report formulas", patched)

