# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ElevatorUnit(models.Model):
    _name = 'elevator.unit'
    _description = 'Elevator Physical Unit / Asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    name = fields.Char(
        string='Elevator Serial / Tag',
        required=True,
        tracking=True,
        copy=False,
        default=lambda self: _('New')
    )
    model_name = fields.Char(
        string='Elevator Model / Package',
        tracking=True,
        help='Manufacturer model or package name.'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer / Building Owner',
        required=True,
        tracking=True
    )
    site_id = fields.Many2one(
        'elevator.site',
        string='Installation Site',
        required=True,
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Operating Company',
        default=lambda self: self.env.company,
        required=True
    )
    origin_company_id = fields.Many2one(
        'res.company',
        string='Sales Origin Company',
        help='Company A that sold the elevator contract.'
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Origin Sale Order',
        check_company=False,
        help='The original sales order signed by Company A.'
    )

    # Technical Characteristics
    capacity_kg = fields.Integer(string='Load Capacity (kg)', default=630)
    persons_capacity = fields.Integer(string='Passenger Capacity (Persons)', default=8)
    speed_mps = fields.Float(string='Rated Speed (m/s)', default=1.0, digits=(3, 2))
    stops_count = fields.Integer(string='Stops / Landings', default=5)
    drive_type = fields.Selection([
        ('vvvf', 'VVVF Gearless Traction'),
        ('geared', 'Geared Traction'),
        ('hydraulic', 'Hydraulic Jack'),
    ], string='Drive / Traction Type', default='vvvf')
    door_type = fields.Selection([
        ('center', 'Center Opening Automatic'),
        ('telescopic', 'Side Telescopic Automatic'),
        ('manual', 'Manual Swing Door'),
    ], string='Door Type', default='center')

    # Status & Lifecycle
    state = fields.Selection([
        ('planned', 'Planned / Awaiting Site Work'),
        ('installation', 'Installation in Progress'),
        ('operational', 'Operational / Active'),
        ('maintenance', 'Under Maintenance'),
        ('out_of_service', 'Out of Service'),
    ], string='Status', default='planned', tracking=True)

    installation_date = fields.Date(string='Commissioning Date', tracking=True)
    warranty_end_date = fields.Date(string='Warranty / Free Service End Date', tracking=True)

    # Relational
    work_order_ids = fields.One2many(
        'elevator.work.order',
        'elevator_unit_id',
        string='Work Orders'
    )
    work_order_count = fields.Integer(
        string='Work Orders Count',
        compute='_compute_counts'
    )
    contract_ids = fields.One2many(
        'elevator.contract',
        'elevator_unit_id',
        string='Service Contracts'
    )
    contract_count = fields.Integer(
        string='Contracts Count',
        compute='_compute_counts'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('elevator.unit') or _('New')
        return super().create(vals_list)

    @api.depends('work_order_ids', 'contract_ids')
    def _compute_counts(self):
        for rec in self:
            rec.work_order_count = len(rec.work_order_ids)
            rec.contract_count = len(rec.contract_ids)

    def action_view_work_orders(self):
        self.ensure_one()
        return {
            'name': _('Work Orders for %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'elevator.work.order',
            'view_mode': 'list,form',
            'domain': [('elevator_unit_id', '=', self.id)],
            'context': {
                'default_elevator_unit_id': self.id,
                'default_site_id': self.site_id.id,
                'default_partner_id': self.partner_id.id,
            },
        }

    def action_view_contracts(self):
        self.ensure_one()
        return {
            'name': _('Service Contracts for %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'elevator.contract',
            'view_mode': 'list,form',
            'domain': [('elevator_unit_id', '=', self.id)],
            'context': {
                'default_elevator_unit_id': self.id,
                'default_site_id': self.site_id.id,
                'default_partner_id': self.partner_id.id,
            },
        }
