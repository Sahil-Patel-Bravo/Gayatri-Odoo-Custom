# -*- coding: utf-8 -*-

import logging

from odoo.fields import Command

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Ensure gst_charge lines and GST report formulas are set up correctly.

    1. Migrate old combined gst_charge lines to new split structure.
    2. Backfill l10n_in_gstr_section on P&F base gst_charge lines.
    3. Clear GSTR section on P&F tax gst_charge lines.
    4. Patch GSTR1, GSTR-2B, and GSTR-3B domain formulas.
    """
    # --- 1. Migrate old combined gst_charge lines to split structure ---
    _migrate_gst_charge_lines(env)

    # --- 2. Backfill GSTR section on P&F base gst_charge lines ---
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


def _migrate_gst_charge_lines(env):
    """Migrate old single combined gst_charge lines to new split structure.

    Old: 1 line named 'GST Charges' with P&F base + tax combined.
    New: 3 lines — 'P&F Charges' (base) + 'P&F 9% SGST' + 'P&F 9% CGST'.

    Skips invoices that have reconciled payments.
    """
    # Find posted invoices/bills with old combined gst_charge line
    old_gc_lines = env['account.move.line'].search([
        ('display_type', '=', 'gst_charge'),
        ('name', '=', 'GST Charges'),
        ('move_id.state', '=', 'posted'),
    ])

    if not old_gc_lines:
        _logger.info("No old GST Charges lines to migrate")
        return

    move_ids = old_gc_lines.mapped('move_id')
    _logger.info("Found %d invoices/bills with old GST Charges lines", len(move_ids))

    migrated = 0
    skipped = 0

    for move in move_ids:
        # Skip if any payment is reconciled
        payment_lines = move.line_ids.filtered(
            lambda l: l.display_type == 'payment_term'
        )
        has_reconciliation = any(
            l.matched_debit_ids or l.matched_credit_ids
            for l in payment_lines
        )
        if has_reconciliation:
            skipped += 1
            continue

        try:
            # Reset to draft
            move.button_draft()

            # Delete old gst_charge lines
            old_lines = move.line_ids.filtered(
                lambda l: l.display_type == 'gst_charge'
            )
            cmds = [Command.delete(l.id) for l in old_lines]

            # Touch pf_gst_per to trigger recompute
            first_line = move.invoice_line_ids[:1]
            if first_line and first_line.pf_gst_per:
                cmds.append(Command.update(
                    first_line.id,
                    {'pf_gst_per': first_line.pf_gst_per + 0.001},
                ))
                move.write({'line_ids': cmds})
                # Set it back to original value
                move.write({'line_ids': [
                    Command.update(first_line.id, {'pf_gst_per': first_line.pf_gst_per - 0.001}),
                ]})
            else:
                move.write({'line_ids': cmds})

            # Re-post
            move.action_post()
            migrated += 1

        except Exception as e:
            _logger.warning(
                "Failed to migrate %s: %s — reverting to posted",
                move.name, e,
            )
            env.cr.rollback()
            skipped += 1

    env.cr.commit()
    _logger.info(
        "Migrated %d invoices/bills, skipped %d (reconciled or error)",
        migrated, skipped,
    )
