# -*- coding: utf-8 -*-

from markupsafe import Markup

from odoo import models, fields, api, _
from odoo.fields import Command
from odoo.tools import frozendict


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
    gst_charge_key = fields.Binary(
        compute='_compute_gst_charge_key', exportable=False,
    )

    @api.onchange('product_id')
    def onchange_product_pf_gst(self):
        if self.product_id:
            self.is_hilti = self.product_id.is_hilti
            self.pf_gst_per = self.product_id.pf_gst if self.product_id.is_hilti else 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('product_id'):
                if 'is_hilti' not in vals:
                    product = self.env['product.product'].browse(vals['product_id'])
                    vals['is_hilti'] = product.is_hilti
                    vals['pf_gst_per'] = product.pf_gst if product.is_hilti else 0
                elif not vals.get('is_hilti'):
                    vals['pf_gst_per'] = 0
        return super().create(vals_list)

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

    def _compute_gst_charge_key(self):
        for line in self:
            if line.display_type == 'gst_charge':
                line.gst_charge_key = frozendict({
                    'move_id': line.move_id.id,
                    'account_id': line.account_id.id if line.account_id else 0,
                })
            else:
                line.gst_charge_key = False

    def _set_l10n_in_gstr_section(self, tax_tags_dict):
        super()._set_l10n_in_gstr_section(tax_tags_dict)
        for line in self.filtered(lambda l: l.display_type == 'gst_charge'):
            # Only set section on the P&F *base* line (name is 'P&F Charges' or 'GST Charges').
            # P&F tax lines must NOT get a section — their amounts
            # are injected via the Python override on account.report.
            if line.name in ('P&F Charges', 'GST Charges'):
                product_section = line.move_id.line_ids.filtered(
                    lambda l: l.display_type == 'product'
                    and l.l10n_in_gstr_section
                    and l.l10n_in_gstr_section not in ('sale_out_of_scope', 'purchase_out_of_scope')
                )[:1].l10n_in_gstr_section
                if product_section:
                    line.l10n_in_gstr_section = product_section
            else:
                line.l10n_in_gstr_section = False


class AccountMove(models.Model):
    _inherit = 'account.move'

    needed_gst_charge = fields.Binary(
        compute='_compute_needed_gst_charge', exportable=False,
    )
    needed_gst_charge_dirty = fields.Boolean(
        compute='_compute_needed_gst_charge',
    )

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

    def _get_pf_tax_amounts_by_tag(self):
        """Compute P&F tax amounts grouped by GST tag for all invoice lines."""
        self.ensure_one()
        gst_tag_refs = {
            'igst': self.env.ref('l10n_in.tax_tag_igst', raise_if_not_found=False),
            'cgst': self.env.ref('l10n_in.tax_tag_cgst', raise_if_not_found=False),
            'sgst': self.env.ref('l10n_in.tax_tag_sgst', raise_if_not_found=False),
            'cess': self.env.ref('l10n_in.tax_tag_cess', raise_if_not_found=False),
        }
        gst_tags = {k: v for k, v in gst_tag_refs.items() if v}
        amounts_by_tag = {}
        currency = self.currency_id
        for line in self.invoice_line_ids:
            if not line.pf_gst_amount:
                continue
            for tax in line.tax_ids:
                children = tax.children_tax_ids if tax.amount_type == 'group' else tax
                for child in children:
                    pf_tax_amt = currency.round(line.pf_gst_amount * child.amount / 100)
                    if not pf_tax_amt:
                        continue
                    tax_rep_tags = child.invoice_repartition_line_ids.filtered(
                        lambda r: r.repartition_type == 'tax'
                    ).tag_ids
                    for tag_key, tag in gst_tags.items():
                        if tag in tax_rep_tags:
                            amounts_by_tag[tag] = currency.round(
                                amounts_by_tag.get(tag, 0.0) + pf_tax_amt
                            )
        return amounts_by_tag

    # -------------------------------------------------------------------------
    # GST-charge dynamic sync
    # -------------------------------------------------------------------------

    @api.depends(
        'invoice_line_ids.pf_gst_amount',
        'invoice_line_ids.tax_ids',
        'move_type',
        'journal_id',
    )
    def _compute_needed_gst_charge(self):
        for move in self:
            move.needed_gst_charge = {}
            move.needed_gst_charge_dirty = True

            if not move.is_invoice(True):
                continue

            currency = move.currency_id or self.env.company.currency_id
            gst_base = currency.round(
                sum(move.invoice_line_ids.mapped('pf_gst_amount'))
            )
            if not gst_base:
                continue

            sign = -1 if move.move_type in ('out_invoice', 'in_refund') else 1
            is_refund = move.move_type in ('out_refund', 'in_refund')

            # --- P&F base line (goes to journal default / sales account) ---
            base_account_id = (
                move.journal_id.default_account_id.id
                if move.journal_id.default_account_id
                else False
            )
            base_balance = sign * abs(gst_base)
            base_key = frozendict({
                'move_id': move.id,
                'account_id': base_account_id or 0,
            })
            move.needed_gst_charge[base_key] = {
                'name': 'P&F Charges',
                'balance': base_balance,
                'amount_currency': base_balance,
                'account_id': base_account_id,
                'quantity': 1,
                'price_unit': abs(gst_base),
            }

            # --- P&F tax lines (one per tax account) ---
            tax_agg = {}  # {account_id: {'amount': float, 'name': str}}
            rep_field = (
                'refund_repartition_line_ids' if is_refund
                else 'invoice_repartition_line_ids'
            )
            for line in move.invoice_line_ids:
                if not line.pf_gst_amount:
                    continue
                for tax in line.tax_ids:
                    children = (
                        tax.children_tax_ids
                        if tax.amount_type == 'group'
                        else tax
                    )
                    for child in children:
                        pf_tax_amt = currency.round(
                            line.pf_gst_amount * child.amount / 100
                        )
                        if not pf_tax_amt:
                            continue
                        rep_lines = child[rep_field].filtered(
                            lambda r: r.repartition_type == 'tax'
                        )
                        tax_acct = rep_lines.account_id
                        acct_id = tax_acct.id if tax_acct else 0
                        if acct_id in tax_agg:
                            tax_agg[acct_id]['amount'] += pf_tax_amt
                        else:
                            tax_agg[acct_id] = {
                                'amount': pf_tax_amt,
                                'name': f'P&F {child.name}',
                                'account_id': tax_acct.id if tax_acct else False,
                            }

            for acct_id, data in tax_agg.items():
                tax_balance = sign * abs(data['amount'])
                tax_key = frozendict({
                    'move_id': move.id,
                    'account_id': acct_id,
                })
                if tax_key in move.needed_gst_charge:
                    # Collision with base account – merge (very rare)
                    existing = move.needed_gst_charge[tax_key]
                    existing['balance'] = currency.round(
                        existing['balance'] + tax_balance
                    )
                    existing['amount_currency'] = existing['balance']
                    existing['price_unit'] = abs(existing['balance'] / sign) if sign else 0
                    continue

                move.needed_gst_charge[tax_key] = {
                    'name': data['name'],
                    'balance': tax_balance,
                    'amount_currency': tax_balance,
                    'account_id': data['account_id'],
                    'quantity': 1,
                    'price_unit': abs(data['amount']),
                }

    def _get_sync_stack(self, container):
        stack, update_containers = super()._get_sync_stack(container)

        gst_container = {'records': self.env['account.move']}

        orig_update = update_containers

        def patched_update():
            result = orig_update()
            gst_container['records'] = container['records'].filtered(
                lambda m: m.is_invoice(True)
            )
            return result

        patched_update()

        stack.append((8, self._sync_dynamic_line(
            existing_key_fname='gst_charge_key',
            needed_vals_fname='needed_gst_charge',
            needed_dirty_fname='needed_gst_charge_dirty',
            line_type='gst_charge',
            container=gst_container,
        )))

        return stack, patched_update

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
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                    # gst_charge excluded – P&F amounts added manually below
                else:
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            sign = move.direction_sign

            gst_amount = move.currency_id.round(
                sum(move.invoice_line_ids.mapped('pf_gst_amount'))
            )
            gst_amount_line = move.currency_id.round(move.get_total_tax_on_gst())
            pf_total = move.currency_id.round(gst_amount + gst_amount_line)

            amount_untaxed = move.currency_id.round(sign * total_untaxed_currency)
            move.amount_untaxed = move.currency_id.round(amount_untaxed + gst_amount)
            move.amount_tax = move.currency_id.round(
                sign * total_tax_currency + gst_amount_line
            )
            amount_total = move.currency_id.round(sign * total_currency)
            move.amount_total = move.currency_id.round(
                amount_total + pf_total
            )

            move.amount_residual = move.currency_id.round(
                -sign * total_residual_currency
            )

            # The *_signed fields feed _compute_needed_terms which sets the
            # payment-term line balance.  They MUST include P&F so that the
            # payment-term amount balances the gst_charge line.
            move.amount_untaxed_signed = move.currency_id.round(
                -total_untaxed + gst_amount
            )
            move.amount_untaxed_in_currency_signed = move.currency_id.round(
                -total_untaxed_currency + gst_amount
            )
            move.amount_tax_signed = move.currency_id.round(
                -total_tax + gst_amount_line
            )
            move.amount_total_signed = (
                abs(total) if move.move_type == 'entry'
                else move.currency_id.round(-total + pf_total)
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

    # -------------------------------------------------------------------------
    # Server Action: Migrate old P&F lines
    # -------------------------------------------------------------------------

    def action_migrate_pf_gst_lines(self):
        """Migrate old single 'GST Charges' line to new split structure.

        Called from server action on selected invoices/bills.
        Handles reconciled invoices by unreconciling → migrating → re-reconciling.
        Logs all changes in the chatter via OdooBot.
        Uses savepoints so one failure doesn't block all others.
        """
        import logging
        _logger = logging.getLogger(__name__)

        moves_to_migrate = self.filtered(
            lambda m: m.state == 'posted'
            and m.is_invoice(True)
            and m.line_ids.filtered(
                lambda l: l.display_type == 'gst_charge'
                and l.name == 'GST Charges'
            )
            and any(il.pf_gst_amount for il in m.invoice_line_ids)
        )

        if not moves_to_migrate:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'P&F Migration',
                    'message': 'No invoices/bills need migration.',
                    'type': 'warning',
                    'sticky': False,
                },
            }

        migrated = []
        failed = []

        for move in moves_to_migrate:
            sp = self.env.cr.savepoint()
            try:
                self._migrate_single_move(move)
                sp.close()
                migrated.append(move.name)
            except Exception as e:
                sp.rollback()
                _logger.warning("Migration failed for %s: %s", move.name, e)
                failed.append(f"{move.name}: {e}")
                move.invalidate_recordset()

        msg_parts = []
        if migrated:
            msg_parts.append(f"Migrated {len(migrated)} invoice(s).")
        if failed:
            msg_parts.append(
                f"Failed {len(failed)}: " + ", ".join(failed[:10])
            )
            if len(failed) > 10:
                msg_parts.append(f"... and {len(failed) - 10} more.")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'P&F Migration Complete',
                'message': " ".join(msg_parts),
                'type': 'success' if not failed else 'warning',
                'sticky': True,
            },
        }

    def _migrate_single_move(self, move):
        old_gc = move.line_ids.filtered(
            lambda l: l.display_type == 'gst_charge'
        )
        old_info = ", ".join(
            f"{l.name} ({l.account_id.code}: ₹{abs(l.balance):.2f})"
            for l in old_gc
        )

        # Save reconciliation info
        pay_lines = move.line_ids.filtered(
            lambda l: l.display_type == 'payment_term'
        )
        reconcile_info = []
        for pl in pay_lines:
            for partial in pl.matched_debit_ids:
                reconcile_info.append({
                    'pay_line_account': pl.account_id,
                    'counterpart': partial.debit_move_id,
                    'amount': partial.amount,
                })
            for partial in pl.matched_credit_ids:
                reconcile_info.append({
                    'pay_line_account': pl.account_id,
                    'counterpart': partial.credit_move_id,
                    'amount': partial.amount,
                })

        # Unreconcile if needed
        if reconcile_info:
            pay_lines.remove_move_reconcile()

        # Reset to draft
        move.button_draft()

        # Delete old gst_charge lines and trigger sync
        cmds = [Command.delete(l.id) for l in old_gc]
        first_line = move.invoice_line_ids[:1]
        if first_line and first_line.pf_gst_per:
            orig_pf = first_line.pf_gst_per
            cmds.append(Command.update(
                first_line.id, {'pf_gst_per': orig_pf + 0.001},
            ))
            move.write({'line_ids': cmds})
            move.write({'line_ids': [
                Command.update(first_line.id, {'pf_gst_per': orig_pf}),
            ]})
        else:
            move.write({'line_ids': cmds})

        # Re-post
        move.action_post()

        # Re-reconcile
        if reconcile_info:
            for info in reconcile_info:
                pay_line = move.line_ids.filtered(
                    lambda l: l.display_type == 'payment_term'
                    and l.account_id == info['pay_line_account']
                )[:1]
                if pay_line and info['counterpart'].exists():
                    (pay_line + info['counterpart']).reconcile()

        # Log in chatter
        new_gc = move.line_ids.filtered(
            lambda l: l.display_type == 'gst_charge'
        )
        new_info = ", ".join(
            f"{l.name} ({l.account_id.code}: ₹{abs(l.balance):.2f})"
            for l in new_gc
        )

        body = Markup(
            "<strong>P&amp;F Charges Updated</strong><br/>"
            "<strong>Old:</strong> %s<br/>"
            "<strong>New:</strong> %s"
        ) % (old_info, new_info)
        move.message_post(
            body=body,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
