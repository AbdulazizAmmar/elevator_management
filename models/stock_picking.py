# -*- coding: utf-8 -*-
from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    elevator_site_id = fields.Many2one(
        'elevator.site',
        string='Site Destination',
        help='Elevator installation site location where goods are delivered.'
    )
    elevator_work_order_id = fields.Many2one(
        'elevator.work.order',
        string='Linked Elevator Work Order',
        check_company=False,
        help='Work order in Company B that will consume or install these delivered materials.'
    )
