# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    pf_gst_per = fields.Float("P&F Percentage")
    pf_gst_amount = fields.Float("P&F Amount", compute="compute_on_pf", store=True)
    is_hilti = fields.Boolean()
    is_pf_line = fields.Boolean("Is PF Line")
    display_type = fields.Selection(
        selection_add=[('gst_charge', 'GST Charge')],
        ondelete={'gst_charge': 'cascade'}
    )

    @api.onchange('product_id')
    def onchange_product_pf_gst(self):
        if self.product_id:
            self.pf_gst_per = self.product_id.pf_gst
            self.is_hilti = self.product_id.is_hilti

    @api.depends("pf_gst_per", "tax_ids", "price_unit", "quantity", "discount", "currency_id")
    def compute_on_pf(self):
        for rec in self:
            price_subtotal = rec.price_unit * rec.quantity
            discount = rec.currency_id.round(price_subtotal * rec.discount / 100)
            price_subtotal = rec.currency_id.round(price_subtotal - discount)
            rec.pf_gst_amount = rec.currency_id.round(price_subtotal * rec.pf_gst_per / 100)

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id')
    def _compute_totals(self):
        AccountTax = self.env['account.tax']
        for line in self:
            if line.display_type not in ('product', 'cogs'):
                line.price_total = line.price_subtotal = False
                continue

            base_line = line.move_id._prepare_product_base_line_for_taxes_computation(line)
            AccountTax._add_tax_details_in_base_line(base_line, line.company_id)
            raw_subtotal = base_line['tax_details']['raw_total_excluded_currency']
            line.price_subtotal = line.currency_id.round(raw_subtotal + line.pf_gst_amount)
            line.price_total = base_line['tax_details']['raw_total_included_currency']

    def create(self, vals):
        res = super().create(vals)
        if not self._context.get('one_time'):
            res.move_id._add_gst_charge_line()
        return res

    def write(self, vals):
        res = super().write(vals)
        if not self._context.get('one_time'):
            self.move_id._add_gst_charge_line()
        return res


class AccountMove(models.Model):
    _inherit = 'account.move'

    def create(self, vals):
        res = super().create(vals)
        if not self._context.get('one_time'):
            res._add_gst_charge_line()
        return res

    def write(self, vals):
        res = super().write(vals)
        if not self._context.get('one_time'):
            self._add_gst_charge_line()
        return res

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def get_pf_name(self):
        for rec in self:
            names_set = set(rec.invoice_line_ids.mapped('pf_gst_per'))
            if names_set:
                return ",".join([str(n) for n in names_set])

    def get_total_gst(self):
        for rec in self:
            return rec.currency_id.round(
                sum(rec.invoice_line_ids.mapped("pf_gst_amount"))
            )

    def get_total_tax_on_gst(self, tax_id=False):
        for rec in self:
            line_amounts = []
            for line in rec.invoice_line_ids:
                if not line.pf_gst_amount:
                    continue
                line_tax_amount = 0.0
                for tax in line.tax_ids:
                    if tax.amount_type == "group":
                        for child_tax in tax.children_tax_ids:
                            if tax_id:
                                if child_tax.tax_group_id.id == tax_id:
                                    line_tax_amount += rec.currency_id.round(
                                        line.pf_gst_amount * child_tax.amount / 100
                                    )
                            else:
                                line_tax_amount += rec.currency_id.round(
                                    line.pf_gst_amount * child_tax.amount / 100
                                )
                    else:
                        if tax_id:
                            if tax.tax_group_id.id == tax_id:
                                line_tax_amount += rec.currency_id.round(
                                    line.pf_gst_amount * tax.amount / 100
                                )
                        else:
                            line_tax_amount += rec.currency_id.round(
                                line.pf_gst_amount * tax.amount / 100
                            )
                line_amounts.append(line_tax_amount)
            return rec.currency_id.round(sum(line_amounts))

    def _add_gst_charge_line(self):
        for record in self:
            if record.state == "draft" and record.move_type in (
                "out_invoice", "in_invoice", "out_refund", "in_refund"
            ):
                invoice_line_ids = record.line_ids.filtered(
                    lambda line: line.display_type == "gst_charge"
                )

                gst_total = record.currency_id.round(
                    sum(record.invoice_line_ids.mapped('pf_gst_amount'))
                )
                gst_amount_line = record.currency_id.round(
                    record.get_total_tax_on_gst()
                )
                total_amount = record.currency_id.round(gst_total + gst_amount_line)

                if record.move_type in ("out_invoice", "in_refund"):
                    final_balance = -abs(total_amount)
                else:
                    final_balance = abs(total_amount)

                if invoice_line_ids:
                    invoice_line_ids.with_context(one_time=True).write({
                        'balance': final_balance,
                        'amount_currency': final_balance,
                    })
                else:
                    record.with_context(one_time=True).write({
                        'line_ids': [(0, 0, {
                            'name': 'GST Charges',
                            'quantity': 1,
                            'display_type': 'gst_charge',
                            'price_unit': abs(total_amount),
                            'balance': final_balance,
                            'amount_currency': final_balance,
                            'account_id': record.journal_id.default_account_id.id,
                        })]
                    })

                # ---------------------------------------------------------------
                # KEY FIX for "Amount Due missing":
                # After writing the gst_charge line we must force Odoo to
                # re-synchronise the payment-term (receivable/payable) line.
                # Without this, the payment-term line balance stays at the
                # pre-P&F value so Amount Due is always short by the P&F total.
                # We use one_time=True to prevent our own write() from looping.
                # ---------------------------------------------------------------
                record.with_context(one_time=True)._synchronize_business_models({'line_ids'})

    # -------------------------------------------------------------------------
    # _compute_amount
    # -------------------------------------------------------------------------

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.origin_payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.origin_payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'state',
    )
    def _compute_amount(self):
        for move in self:
            total_untaxed, total_untaxed_currency = 0.0, 0.0
            total_tax, total_tax_currency = 0.0, 0.0
            total_residual, total_residual_currency = 0.0, 0.0
            total, total_currency = 0.0, 0.0

            for line in move.line_ids:
                if move.is_invoice(True):
                    if line.display_type == 'tax' or (
                        line.display_type == 'rounding' and line.tax_repartition_line_id
                    ):
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type in ('product', 'rounding'):
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type == 'payment_term':
                        # payment_term line balance is set by Odoo to balance the
                        # full journal entry (including gst_charge line) after
                        # _synchronize_business_models runs — so amount_residual
                        # here will already reflect the P&F amount correctly.
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                    # gst_charge lines excluded here; added via gst_amount below
                else:
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            sign = move.direction_sign

            gst_amount = move.currency_id.round(
                sum(move.invoice_line_ids.mapped('pf_gst_amount'))
            )
            gst_amount_line = move.currency_id.round(move.get_total_tax_on_gst())

            amount_untaxed = move.currency_id.round(sign * total_untaxed_currency)
            move.amount_untaxed = move.currency_id.round(amount_untaxed + gst_amount)
            move.amount_tax = move.currency_id.round(
                sign * total_tax_currency + gst_amount_line
            )
            amount_total = move.currency_id.round(sign * total_currency)
            move.amount_total = move.currency_id.round(
                amount_total + gst_amount + gst_amount_line
            )

            # amount_residual drives "Amount Due".
            # After _synchronize_business_models the payment_term line balance
            # already includes the gst_charge, so we read it directly.
            move.amount_residual = move.currency_id.round(-sign * total_residual_currency)

            move.amount_untaxed_signed = -total_untaxed
            move.amount_untaxed_in_currency_signed = -total_untaxed_currency
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = (
                abs(total) if move.move_type == 'entry' else -total
            )
            move.amount_residual_signed = total_residual
            move.amount_total_in_currency_signed = (
                abs(move.amount_total)
                if move.move_type == 'entry'
                else -(sign * move.amount_total)
            )

    # -------------------------------------------------------------------------
    # Tax totals widget
    # -------------------------------------------------------------------------

    @api.depends_context('lang')
    @api.depends(
        'invoice_line_ids.currency_rate',
        'invoice_line_ids.tax_base_amount',
        'invoice_line_ids.tax_line_id',
        'invoice_line_ids.price_total',
        'invoice_line_ids.price_subtotal',
        'invoice_payment_term_id',
        'partner_id',
        'currency_id',
    )
    def _compute_tax_totals(self):
        for move in self:
            if move.is_invoice(include_receipts=True):
                base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()
                move.tax_totals = self.env['account.tax']._get_tax_totals_summary(
                    base_lines=base_lines,
                    currency=move.currency_id,
                    company=move.company_id,
                    cash_rounding=move.invoice_cash_rounding_id,
                )
                move.tax_totals['display_in_company_currency'] = (
                    move.company_id.display_invoice_tax_company_currency
                    and move.company_currency_id != move.currency_id
                    and move.tax_totals['has_tax_groups']
                    and move.is_sale_document(include_receipts=True)
                )

                gst_amount = move.currency_id.round(
                    sum(move.invoice_line_ids.mapped('pf_gst_amount'))
                )
                gst_amount_line = move.currency_id.round(move.get_total_tax_on_gst())

                for subtotal in move.tax_totals.get('subtotals', []):
                    if subtotal['name'] == 'Untaxed Amount':
                        subtotal['base_amount_currency'] = move.currency_id.round(
                            subtotal['base_amount_currency'] + gst_amount
                        )

                    for tax_group in subtotal.get('tax_groups', []):
                        line_gst_tax = move.currency_id.round(
                            move.get_total_tax_on_gst(tax_id=tax_group.get('id'))
                        )
                        if move.move_type in ("out_invoice", "out_refund"):
                            tax_group['tax_amount'] = move.currency_id.round(
                                tax_group['tax_amount'] + line_gst_tax
                            )
                        tax_group['tax_amount_currency'] = move.currency_id.round(
                            tax_group['tax_amount_currency'] + line_gst_tax
                        )

                move.tax_totals['base_amount_currency'] = move.currency_id.round(
                    move.tax_totals['base_amount_currency'] + gst_amount + gst_amount_line
                )
                move.tax_totals['total_amount_currency'] = move.currency_id.round(
                    move.tax_totals['total_amount_currency'] + gst_amount + gst_amount_line
                )
                move.tax_totals['total_amount'] = move.currency_id.round(
                    move.tax_totals['total_amount'] + gst_amount + gst_amount_line
                )
            else:
                move.tax_totals = None