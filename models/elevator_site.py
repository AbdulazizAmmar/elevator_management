# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ElevatorSite(models.Model):
    _name = 'elevator.site'
    _description = 'Elevator Installation Site'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    name = fields.Char(
        string='Site / Building Name',
        required=True,
        tracking=True,
        help='Name of the building, compound, or project location.'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer / Owner',
        required=True,
        tracking=True,
        help='The customer who purchased the elevator.'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )

    # Address
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street 2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    zip = fields.Char(string='Zip / Postal Code')
    country_id = fields.Many2one('res.country', string='Country')

    # Site Contact on Ground
    contact_name = fields.Char(string='Site Supervisor / Contact')
    contact_phone = fields.Char(string='Contact Phone')
    contact_email = fields.Char(string='Contact Email')

    # Shaft & Technical Characteristics
    floors_count = fields.Integer(string='Number of Floors / Landings', default=1)
    shaft_width = fields.Float(string='Shaft Width (m)', digits=(4, 2))
    shaft_depth = fields.Float(string='Shaft Depth (m)', digits=(4, 2))
    pit_depth = fields.Float(string='Pit Depth (m)', digits=(4, 2))
    overhead_height = fields.Float(string='Headroom / Overhead (m)', digits=(4, 2))
    machine_room_type = fields.Selection([
        ('machine_room', 'Standard Machine Room'),
        ('mrl', 'Machine Room-Less (MRL)'),
        ('hydraulic', 'Hydraulic Unit')
    ], string='Engine / Room Type', default='mrl')
    power_supply = fields.Char(string='Power Supply', default='3-Phase 380V 50Hz')

    notes = fields.Text(string='Site Access / Gate Notes')

    # Relational links
    elevator_unit_ids = fields.One2many(
        'elevator.unit',
        'site_id',
        string='Elevator Units'
    )
    unit_count = fields.Integer(
        string='Units Count',
        compute='_compute_unit_count'
    )
    work_order_ids = fields.One2many(
        'elevator.work.order',
        'site_id',
        string='Work Orders'
    )
    work_order_count = fields.Integer(
        string='Work Orders Count',
        compute='_compute_work_order_count'
    )

    @api.depends('elevator_unit_ids')
    def _compute_unit_count(self):
        for rec in self:
            rec.unit_count = len(rec.elevator_unit_ids)

    @api.depends('work_order_ids')
    def _compute_work_order_count(self):
        for rec in self:
            rec.work_order_count = len(rec.work_order_ids)

    def action_view_units(self):
        self.ensure_one()
        return {
            'name': _('Elevator Units on Site'),
            'type': 'ir.actions.act_window',
            'res_model': 'elevator.unit',
            'view_mode': 'list,form',
            'domain': [('site_id', '=', self.id)],
            'context': {'default_site_id': self.id, 'default_partner_id': self.partner_id.id},
        }

    def action_view_work_orders(self):
        self.ensure_one()
        return {
            'name': _('Work Orders on Site'),
            'type': 'ir.actions.act_window',
            'res_model': 'elevator.work.order',
            'view_mode': 'list,form',
            'domain': [('site_id', '=', self.id)],
            'context': {'default_site_id': self.id, 'default_partner_id': self.partner_id.id},
        }
