# -*- coding: utf-8 -*-

from odoo import models


class L10nInAccountReturn(models.Model):
    _inherit = 'l10n_in.account.return'

    def _get_tax_details(self, domain):
        tax_vals_map = super()._get_tax_details(domain)
        for move, line_vals in tax_vals_map.items():
            for base_line, vals in line_vals.items():
                pf_amount = base_line.pf_gst_amount
                if pf_amount:
                    vals['base_amount'] = move.currency_id.round(
                        vals['base_amount'] + pf_amount
                    )
        return tax_vals_map
