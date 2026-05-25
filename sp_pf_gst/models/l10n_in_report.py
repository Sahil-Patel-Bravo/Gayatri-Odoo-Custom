# -*- coding: utf-8 -*-

from ast import literal_eval

from odoo import models
from odoo.tools import SQL


class AccountReturn(models.Model):
    _inherit = 'account.return'

    def _get_tax_details(self, domain):
        tax_vals_map = super()._get_tax_details(domain)
        gst_tags = {
            'igst': self.env.ref('l10n_in.tax_tag_igst'),
            'cgst': self.env.ref('l10n_in.tax_tag_cgst'),
            'sgst': self.env.ref('l10n_in.tax_tag_sgst'),
            'cess': self.env.ref('l10n_in.tax_tag_cess'),
        }
        for move, line_vals in list(tax_vals_map.items()):
            gst_charge_lines = [l for l in line_vals if l.display_type == 'gst_charge']
            for line in gst_charge_lines:
                del line_vals[line]
            if not line_vals:
                del tax_vals_map[move]
                continue
            for base_line, vals in line_vals.items():
                pf_amount = base_line.pf_gst_amount
                if not pf_amount:
                    continue
                currency = move.currency_id
                vals['base_amount'] = currency.round(vals['base_amount'] + pf_amount)
                for tax in base_line.tax_ids:
                    children = tax.children_tax_ids if tax.amount_type == 'group' else tax
                    for child in children:
                        pf_tax_amt = currency.round(pf_amount * child.amount / 100)
                        tax_rep_tags = child.invoice_repartition_line_ids.filtered(
                            lambda r: r.repartition_type == 'tax'
                        ).tag_ids
                        for tax_type, tag in gst_tags.items():
                            if tag in tax_rep_tags:
                                vals[tax_type] = currency.round(vals[tax_type] + pf_tax_amt)
        return tax_vals_map


class AccountReport(models.Model):
    _inherit = 'account.report'

    def _compute_formula_batch_with_engine_domain(
        self, options, date_scope, formulas_dict, current_groupby,
        next_groupby, offset=0, limit=None, warnings=None,
    ):
        rslt = super()._compute_formula_batch_with_engine_domain(
            options, date_scope, formulas_dict, current_groupby,
            next_groupby, offset=offset, limit=limit, warnings=warnings,
        )

        gst_report_ids = set()
        for ref in (
            'l10n_in_reports.account_report_gstr1',
            'l10n_in_reports.account_report_gstr2b',
            'l10n_in_reports.account_report_gstr3b',
        ):
            report = self.env.ref(ref, raise_if_not_found=False)
            if report:
                gst_report_ids.add(report.id)
        if options.get('report_id') not in gst_report_ids:
            return rslt

        pf_cache = {}

        for key in list(rslt.keys()):
            formula, expressions = key
            try:
                domain = literal_eval(formula)
            except (ValueError, SyntaxError):
                continue

            sections = None
            is_base = False
            tag_id = None

            for term in domain:
                if not isinstance(term, (list, tuple)) or len(term) != 3:
                    continue
                field, op, value = term
                if field == 'l10n_in_gstr_section' and op == '=':
                    sections = [value]
                elif field == 'l10n_in_gstr_section' and op == 'in':
                    sections = list(value)
                elif field == 'display_type' and (
                    (op == '=' and value == 'product')
                    or (op == 'in' and 'product' in value)
                ):
                    is_base = True
                elif field == 'tax_tag_ids':
                    tag_id = value if op == '=' else (
                        value[0] if op == 'in' and value else None
                    )

            if not sections or (not is_base and tag_id is None):
                continue

            pf_addition = 0.0
            for section in sections:
                if section not in pf_cache:
                    pf_cache[section] = self._sp_pf_gst_amounts_for_section(
                        options, date_scope, section,
                    )
                pf_base, pf_tax_by_tag, gst_charge_bal = pf_cache[section]
                if is_base:
                    # The domain may include gst_charge lines.  Depending on
                    # invoice structure (old combined line vs new split lines)
                    # the gst_charge balance may contain P&F tax.  Subtract
                    # any excess so only P&F base remains in the total.
                    excess = gst_charge_bal - pf_base
                    pf_addition -= excess
                elif tag_id in pf_tax_by_tag:
                    # P&F tax lines don't have a GSTR section, so they are
                    # not captured by the tax domain – add them here.
                    pf_addition += pf_tax_by_tag[tag_id]

            if not pf_addition:
                continue

            result = rslt[key]
            if isinstance(result, dict):
                result['sum'] += pf_addition
            elif isinstance(result, list):
                for _grouping_key, totals in result:
                    totals['sum'] += pf_addition

        return rslt

    def _get_expression_audit_aml_domain(self, expression_to_audit, options):
        domain = super()._get_expression_audit_aml_domain(expression_to_audit, options)

        gst_report_ids = set()
        for ref in (
            'l10n_in_reports.account_report_gstr1',
            'l10n_in_reports.account_report_gstr2b',
            'l10n_in_reports.account_report_gstr3b',
        ):
            report = self.env.ref(ref, raise_if_not_found=False)
            if report:
                gst_report_ids.add(report.id)
        if options.get('report_id') not in gst_report_ids:
            return domain

        if not domain or expression_to_audit.engine != 'domain':
            return domain

        # Check if the expression is for tax columns (filters on tax_tag_ids)
        # GSTR-1 tax domains look like: [('l10n_in_gstr_section', '=', 'sale_b2b_regular'), ('tax_tag_ids', '=', 26)]
        sections = []
        tag_id = None
        for term in domain:
            if isinstance(term, (list, tuple)) and len(term) == 3:
                field, op, value = term
                if field == 'l10n_in_gstr_section':
                    if op == '=':
                        sections = [value]
                    elif op == 'in':
                        sections = list(value)
                elif field == 'tax_tag_ids':
                    tag_id = value if op == '=' else (
                        value[0] if op == 'in' and value else None
                    )

        if sections and tag_id:
            # We are auditing a tax column (IGST, CGST, SGST, Cess) for specific sections.
            # Get the P&F tax line IDs for these sections and tag
            pf_tax_line_ids = self._get_sp_pf_gst_tax_line_ids(options, sections, tag_id)
            if pf_tax_line_ids:
                # Add them to the domain using OR ('|') via Domain.OR
                from odoo.fields import Domain
                domain = Domain.OR([domain, [('id', 'in', pf_tax_line_ids)]])

        return domain

    def _get_sp_pf_gst_tax_line_ids(self, options, sections, tag_id):
        # 1. Find all posted invoices in the period whose product lines have GSTR section in `sections`
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        move_domain = [
            ('display_type', '=', 'product'),
            ('l10n_in_gstr_section', 'in', sections),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('move_id.state', '=', 'posted'),
        ]
        move_ids = self.env['account.move.line'].search(move_domain).mapped('move_id').ids
        if not move_ids:
            return []

        # 2. Find repartition lines with this tag
        rep_lines = self.env['account.tax.repartition.line'].search([
            ('repartition_type', '=', 'tax'),
            ('tag_ids', 'in', [tag_id]),
        ])
        tax_accounts = rep_lines.mapped('account_id')
        if not tax_accounts:
            return []

        # 3. Find the gst_charge lines in our move_ids that use these tax accounts
        pf_tax_lines = self.env['account.move.line'].search([
            ('move_id', 'in', move_ids),
            ('display_type', '=', 'gst_charge'),
            ('account_id', 'in', tax_accounts.ids),
        ])
        return pf_tax_lines.ids

    def _sp_pf_gst_amounts_for_section(self, options, date_scope, section):
        """Return (pf_base_sum, {tag_id: pf_tax_sum}, gst_charge_balance).

        *pf_base_sum* and *pf_tax_sum* follow the same sign convention as
        ``balance`` (negative for sales credits).

        *gst_charge_balance* is the total balance of gst_charge lines that
        have this section set.  It may equal pf_base (new split structure)
        or pf_base + pf_tax (old combined structure).
        """
        # --- P&F base total from product lines ---
        domain = [
            ('display_type', '=', 'product'),
            ('l10n_in_gstr_section', '=', section),
            ('pf_gst_amount', '!=', 0),
        ]
        query = self._get_report_query(options, date_scope, domain=domain)

        pf_query = SQL(
            """
            SELECT COALESCE(
                SUM(SIGN(account_move_line.balance) * account_move_line.pf_gst_amount),
                0.0
            )
            FROM %(table_refs)s
            WHERE %(search_cond)s
            """,
            table_refs=query.from_clause,
            search_cond=query.where_clause,
        )
        self.env.cr.execute(pf_query)
        pf_base = self.env.cr.fetchone()[0] or 0.0

        # --- P&F tax amounts by tag ---
        line_query = SQL(
            """
            SELECT account_move_line.id
            FROM %(table_refs)s
            WHERE %(search_cond)s
            """,
            table_refs=query.from_clause,
            search_cond=query.where_clause,
        )
        self.env.cr.execute(line_query)
        line_ids = [r[0] for r in self.env.cr.fetchall()]

        pf_tax_by_tag = {}
        if line_ids:
            gst_tags = {
                k: self.env.ref(f'l10n_in.tax_tag_{k}', raise_if_not_found=False)
                for k in ('igst', 'cgst', 'sgst', 'cess')
            }
            lines = self.env['account.move.line'].browse(line_ids)
            for line in lines:
                sign = -1 if line.balance < 0 else 1
                currency = line.currency_id
                for tax in line.tax_ids:
                    children = (
                        tax.children_tax_ids
                        if tax.amount_type == 'group'
                        else tax
                    )
                    for child in children:
                        pf_tax_amt = sign * currency.round(
                            line.pf_gst_amount * child.amount / 100
                        )
                        tax_rep_tags = child.invoice_repartition_line_ids.filtered(
                            lambda r: r.repartition_type == 'tax'
                        ).tag_ids
                        for tag in gst_tags.values():
                            if tag and tag in tax_rep_tags:
                                pf_tax_by_tag[tag.id] = (
                                    pf_tax_by_tag.get(tag.id, 0.0) + pf_tax_amt
                                )

        # --- gst_charge balance in this section ---
        gc_domain = [
            ('display_type', '=', 'gst_charge'),
            ('l10n_in_gstr_section', '=', section),
        ]
        gc_query = self._get_report_query(options, date_scope, domain=gc_domain)
        gc_bal_query = SQL(
            """
            SELECT COALESCE(SUM(account_move_line.balance), 0.0)
            FROM %(table_refs)s
            WHERE %(search_cond)s
            """,
            table_refs=gc_query.from_clause,
            search_cond=gc_query.where_clause,
        )
        self.env.cr.execute(gc_bal_query)
        gst_charge_bal = self.env.cr.fetchone()[0] or 0.0

        return pf_base, pf_tax_by_tag, gst_charge_bal
