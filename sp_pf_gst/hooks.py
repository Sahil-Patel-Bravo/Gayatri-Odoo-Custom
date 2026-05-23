# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Backfill l10n_in_gstr_section on existing gst_charge lines.

    When the module is upgraded, existing posted invoices already have their
    product lines assigned a section, but the gst_charge lines were never
    processed by _set_l10n_in_gstr_section. This hook copies the section
    from the invoice's first product line to the gst_charge line.
    """
    gst_charge_lines = env['account.move.line'].search([
        ('display_type', '=', 'gst_charge'),
        ('move_id.state', '=', 'posted'),
        ('l10n_in_gstr_section', 'in', [False, 'sale_out_of_scope']),
    ])
    for line in gst_charge_lines:
        product_section = line.move_id.line_ids.filtered(
            lambda l: l.display_type == 'product'
            and l.l10n_in_gstr_section
            and l.l10n_in_gstr_section != 'sale_out_of_scope'
        )[:1].l10n_in_gstr_section
        if product_section:
            line.l10n_in_gstr_section = product_section
