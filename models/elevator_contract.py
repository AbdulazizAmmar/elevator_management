# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import timedelta
from dateutil.relativedelta import relativedelta

class ElevatorContract(models.Model):
    _name = 'elevator.contract'
    _description = 'Elevator Service & Maintenance Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char(
        string='Contract Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer / Client',
        required=True,
        tracking=True
    )
    site_id = fields.Many2one(
        'elevator.site',
        string='Site Location',
        required=True,
        tracking=True
    )
    elevator_unit_id = fields.Many2one(
        'elevator.unit',
        string='Elevator Unit',
        tracking=True
    )

    # Multi-Company Ties
    origin_company_id = fields.Many2one(
        'res.company',
        string='Sales Origin Company (Company A)',
        required=True,
        tracking=True,
        help='Company A that signed the sales and service agreement with the client.'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Executing Service Company (Company B)',
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
        help='Company B that executes the scheduled inspections and maintenance visits.'
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Original Sales Contract (Company A)',
        check_company=False,
        tracking=True
    )

    # Contract Terms
    contract_type = fields.Selection([
        ('warranty', '1-Year Free Service Package (Warranty Included)'),
        ('annual_amc', 'Annual Maintenance Contract (Paid AMC)'),
        ('on_demand', 'On-Demand Service Contract'),
    ], string='Contract Type', default='warranty', required=True, tracking=True)

    date_start = fields.Date(string='Start Date', default=fields.Date.today, required=True, tracking=True)
    date_end = fields.Date(
        string='End Date',
        default=lambda self: fields.Date.today() + relativedelta(years=1),
        required=True,
        tracking=True
    )

    visit_interval_months = fields.Integer(
        string='Visit Frequency (Months)',
        default=1,
        help='Interval in months between routine preventive maintenance inspections (e.g. 1 = Monthly).'
    )
    next_visit_date = fields.Date(
        string='Next Inspection Due',
        compute='_compute_next_visit_date',
        store=True,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='active', tracking=True)

    terms_and_conditions = fields.Text(string='Contract Scope & Coverage Notes')

    # Associated Work Orders
    work_order_ids = fields.One2many(
        'elevator.work.order',
        'contract_id',
        string='Maintenance Work Orders'
    )
    work_order_count = fields.Integer(
        string='Visits Count',
        compute='_compute_work_order_count'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('elevator.contract') or _('New')
        return super().create(vals_list)

    @api.depends('work_order_ids')
    def _compute_work_order_count(self):
        for rec in self:
            rec.work_order_count = len(rec.work_order_ids)

    @api.depends('date_start', 'visit_interval_months', 'work_order_ids.date_planned_start')
    def _compute_next_visit_date(self):
        for rec in self:
            dated_orders = rec.work_order_ids.filtered(lambda w: w.date_planned_start)
            if dated_orders:
                last_visit = dated_orders.sorted(key=lambda w: w.date_planned_start, reverse=True)[0]
                rec.next_visit_date = last_visit.date_planned_start.date() + relativedelta(months=rec.visit_interval_months or 1)
            elif rec.date_start:
                rec.next_visit_date = rec.date_start + relativedelta(months=rec.visit_interval_months or 1)
            else:
                rec.next_visit_date = fields.Date.today()

    def action_schedule_maintenance_visit(self):
        """Generates a scheduled maintenance inspection work order in Company B."""
        self.ensure_one()
        wo_vals = {
            'order_type': 'maintenance',
            'partner_id': self.partner_id.id,
            'site_id': self.site_id.id,
            'elevator_unit_id': self.elevator_unit_id.id if self.elevator_unit_id else False,
            'contract_id': self.id,
            'origin_company_id': self.origin_company_id.id,
            'company_id': self.company_id.id,
            'date_planned_start': fields.Datetime.now() + relativedelta(days=1),
            'notes': _("Routine scheduled inspection under contract %(contract)s (1-Year Free Service / Warranty). "
                       "Materials and replacement parts to be sourced from Company A storage.", contract=self.name)
        }
        work_order = self.env['elevator.work.order'].with_company(self.company_id).create(wo_vals)
        self.message_post(body=_(
            "Scheduled Maintenance Inspection Work Order <b>%(wo)s</b> created for %(comp)s.",
            wo=work_order.name,
            comp=self.company_id.name
        ))
        return {
            'name': _('Maintenance Work Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'elevator.work.order',
            'res_id': work_order.id,
            'view_mode': 'form',
        }

    def action_view_work_orders(self):
        self.ensure_one()
        return {
            'name': _('Maintenance Visits for %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'elevator.work.order',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {
                'default_contract_id': self.id,
                'default_site_id': self.site_id.id,
                'default_partner_id': self.partner_id.id,
                'default_elevator_unit_id': self.elevator_unit_id.id if self.elevator_unit_id else False,
            }
        }
