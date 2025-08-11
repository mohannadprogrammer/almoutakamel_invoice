# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.

###############################################################################
from io import BytesIO
import binascii
import pytz
from odoo.fields import Date

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from num2words import num2words
try:
    import qrcode
except ImportError:
    qrcode = None
try:
    import base64
except ImportError:
    base64 = None


class AccountMove(models.Model):
    """Class for adding new button and a page in account move"""
    _inherit = 'account.move'

    qr = fields.Binary(string="QR Code", compute='generate_qrcode', store=True,
                       help="QR code")
    qr_button = fields.Boolean(string="Qr Button", compute="_compute_qr",
                               help="Is QR button is enable or not")
    qr_page = fields.Boolean(string="Qr Page", compute="_compute_qr",
                             help="Is QR page is enable or not")
    
    ar_total_word = fields.Char(string="Total in word", compute="_compute_ar_total_word",
                             help="Is Total in word ")
    #auto payment fields
    mo_payment_type = fields.Selection(
        selection=[
            ('ajil', 'أجل'),
            ('ghair_ajil', 'غير أجل'),
        ],
        string='Payment Type'
    )

    payment_method_id = fields.Many2one(
        'account.payment.method.line',
        compute='_compute_payment_method_line_id',
        readonly=False, store=True, copy=False,
        
        domain="[('id', 'in', available_payment_method_line_ids)]",
        string='Payment Method'

    )
    available_payment_method_line_ids = fields.Many2many('account.payment.method.line',
        compute='_compute_payment_method_line_fields')
    
    payment_journal_id = fields.Many2one(
        'account.journal',
        domain="[('id', 'in', available_payment_journal_ids)]",
        string ='Payment Journal'
    )
    available_payment_journal_ids = fields.Many2many(
        comodel_name='account.journal',
        compute='_compute_available_payment_journal_ids'
    )
    @api.depends('available_payment_method_line_ids')
    def _compute_payment_method_line_id(self):
        ''' Compute the 'payment_method_line_id' field.
        This field is not computed in '_compute_payment_method_line_fields' because it's a stored editable one.
        '''
        print("dkflsdkf")
        for pay in self:
            available_payment_method_lines = pay.available_payment_method_line_ids

            # Select the first available one by default.
            if pay.payment_method_id in available_payment_method_lines:
                pay.payment_method_id = pay.payment_method_id
            elif available_payment_method_lines:
                pay.payment_method_id = available_payment_method_lines[0]._origin
            else:
                pay.payment_method_id = False
    @api.depends( 'payment_journal_id')
    def _compute_payment_method_line_fields(self):
        for pay in self:
            pay.available_payment_method_line_ids = pay.payment_journal_id._get_available_payment_method_lines('inbound')
            to_exclude = pay._get_payment_method_codes_to_exclude()
            if to_exclude:
                pay.available_payment_method_line_ids = pay.available_payment_method_line_ids.filtered(lambda x: x.code not in to_exclude)
    @api.depends('mo_payment_type')
    def _compute_available_payment_journal_ids(self):
        """
        Get all journals having at least one payment method for inbound/outbound depending on the payment_type.
        """
        journals = self.env['account.journal'].search([
            '|',
            ('company_id', 'parent_of', self.env.company.id),
            ('company_id', 'child_of', self.env.company.id),
            ('type', 'in', ('bank', 'cash')),
        ])
        
        for pay in self:
            # if pay.payment_type == 'inbound':
            pay.available_payment_journal_ids = journals.filtered('inbound_payment_method_line_ids')
            if (pay.mo_payment_type == 'ghair_ajil' ):
                pay.payment_journal_id = journals.filtered('inbound_payment_method_line_ids')[0]

            # else:
                # pay.available_journal_ids = journals.filtered('outbound_payment_method_line_ids')

    def _get_payment_method_codes_to_exclude(self):
        # can be overriden to exclude payment methods based on the payment characteristics
        self.ensure_one()
        return []

   
    
    def action_post(self):
        
        super().action_post()
        for rec in self:
            if rec.mo_payment_type== 'ghair_ajil' :
                payment_created =self.env['account.payment'].search([('ref', '=', rec.name)])
                if not payment_created:
                    payment = rec._create_instant_payment()
                    print("payment created",payment.line_ids[1].id)
                    print("payment created new line",payment.line_ids)
                    # pass the credit line in the payment ti assign it ro the invoice
                    rec.js_assign_outstanding_line(payment.line_ids[1].id)
                else:
                    rec.js_assign_outstanding_line(payment_created.line_ids[1].id)

        
        return False
    
    def _create_instant_payment(self):
        self.ensure_one()

        payment_vals = {
            'payment_type': 'inbound',
            'payment_method_id':self.payment_method_id.id,
            'partner_id': self.partner_id.id,
            'amount': self.amount_total,
            'date': Date.today(),
            'ref': self.name,
            'payment_method_line_id': self.payment_method_id.id,
            'journal_id': self.payment_journal_id.id,
            
            'reconciled_invoice_ids': [(6, 0, [self.id])]
            
        }
        print(payment_vals)
        payment = self.env['account.payment'].create(payment_vals)
        payment.action_post()
        return payment
    
    @api.depends('amount_total')
    def _compute_ar_total_word(self):
        """Compute function for checking the value of a field in settings."""

        for record in self:
            record.ar_total_word = num2words(record.amount_total ,to = 'currency', lang='ar_SA')

            # if record.amount_total:
            #     record.ar_total_word = record.currency_id.amount_to_text(
            #         record.amount_total, 'ar_SA', 'total')
            #     print(record.ar_total_word)
            # else:
            #     record.ar_total_word = ''
    @api.depends('qr_button')
    def _compute_qr(self):
        """Compute function for checking the value of a field in settings."""
        for record in self:
            qr_code = self.env['ir.config_parameter'].sudo().get_param(
                'advanced_vat_invoice.is_qr'
            )
            qr_code_generate_method = self.env[
                'ir.config_parameter'].sudo().get_param(
                'advanced_vat_invoice.generate_qr'
            )
            record.qr_button = (
                True if (
                        qr_code and qr_code_generate_method == 'manually')
                else False
            )
            record.qr_page = (
                True if (
                        qr_code
                        and record.state in ['posted', 'cancelled']
                        and qr_code_generate_method == 'manually'
                        or qr_code_generate_method == 'automatically'
                )
                else False
            )

    def timezone(self, userdate):
        """Function to convert a user's date to their timezone."""
        tz_name = self.env.context.get('tz') or self.env.user.tz
        contex_tz = pytz.timezone(tz_name)
        date_time = pytz.utc.localize(userdate).astimezone(contex_tz)
        return date_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    def string_hexa(self, value):
        """Convert a string to a hexadecimal representation."""
        if value:
            string = str(value)
            string_bytes = string.encode("UTF-8")
            encoded_hex_value = binascii.hexlify(string_bytes)
            hex_value = encoded_hex_value.decode("UTF-8")
            return hex_value

    def hexa(self, tag, length, value):
        """Generate a hex value with tag, length, and value."""
        if tag and length and value:
            hex_string = self.string_hexa(value)
            length = int(len(hex_string) / 2)
            conversion_table = ['0', '1', '2', '3', '4', '5', '6', '7', '8',
                                '9', 'a', 'b', 'c', 'd', 'e', 'f']
            hexadecimal = ''
            while (length > 0):
                remainder = length % 16
                hexadecimal = conversion_table[remainder] + hexadecimal
                length = length // 16
            if len(hexadecimal) == 1:
                hexadecimal = "0" + hexadecimal
            return tag + hexadecimal + hex_string

    def qr_code_data(self):
        """Generate QR code data for the current record."""
        seller_name = str(self.company_id.name)
        seller_vat_no = self.company_id.vat or ''
        seller_hex = self.hexa("01", "0c", seller_name)
        vat_hex = self.hexa("02", "0f", seller_vat_no) or ""
        time_stamp = self.timezone(self.create_date)
        date_hex = self.hexa("03", "14", time_stamp)
        amount_total = self.currency_id._convert(
            self.amount_total,
            self.env.ref('base.SAR'),
            self.env.company, self.invoice_date or fields.Date.today())
        total_with_vat_hex = self.hexa("04", "0a",
                                       str(round(amount_total, 2)))
        amount_tax = self.currency_id._convert(
            self.amount_tax,
            self.env.ref('base.SAR'),
            self.env.company, self.invoice_date or fields.Date.today())
        total_vat_hex = self.hexa("05", "09",
                                  str(round(amount_tax, 2)))
        qr_hex = (seller_hex + vat_hex + date_hex + total_with_vat_hex +
                  total_vat_hex)
        encoded_base64_bytes = base64.b64encode(bytes.fromhex(qr_hex)).decode()
        return encoded_base64_bytes

    @api.depends('state')
    def generate_qrcode(self):
        """Generate and save QR code after the invoice is posted."""
        param = self.env['ir.config_parameter'].sudo()
        qr_code = param.get_param('advanced_vat_invoice.generate_qr')
        for rec in self:
            if rec.state == 'posted':
                if qrcode and base64:
                    if qr_code == 'automatically':
                        qr = qrcode.QRCode(
                            version=4,
                            error_correction=qrcode.constants.ERROR_CORRECT_L,
                            box_size=4,
                            border=1,
                        )
                        qr.add_data(self._origin.qr_code_data())
                        qr.make(fit=True)
                        img = qr.make_image()
                        temp = BytesIO()
                        img.save(temp, format="PNG")
                        qr_image = base64.b64encode(temp.getvalue())
                        rec.qr = qr_image
                else:
                    raise UserError(
                        _('Necessary Requirements To Run This Operation Is '
                          'Not Satisfied'))

    def generate_qr_button(self):
        """Manually generate and save QR code."""
        param = self.env['ir.config_parameter'].sudo()
        qr_code = param.get_param('advanced_vat_invoice.generate_qr')
        for rec in self:
            if qrcode and base64:
                if qr_code == 'manually':
                    qr = qrcode.QRCode(
                        version=4,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=4,
                        border=1,
                    )
                    qr.add_data(self.qr_code_data())
                    qr.make(fit=True)
                    img = qr.make_image()
                    temp = BytesIO()
                    img.save(temp, format="PNG")
                    qr_image = base64.b64encode(temp.getvalue())
                    rec.qr = qr_image
            else:
                raise UserError(
                    _('Necessary Requirements To Run This Operation Is '
                      'Not Satisfied'))
