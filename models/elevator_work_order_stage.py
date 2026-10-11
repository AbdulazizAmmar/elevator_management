# -*- coding: utf-8 -*-
from odoo import models, fields

class ElevatorWorkOrderStage(models.Model):
    _name = 'elevator.work.order.stage'
    _description = 'Elevator Work Order Stage'
    _order = 'sequence asc, id asc'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    stage_type = fields.Selection([
        ('installation', 'Installation'),
        ('maintenance', 'Maintenance / Inspection'),
        ('repair', 'Paid Repair / Parts Replacement'),
        ('all', 'All Work Order Types')
    ], string='Stage Type', default='installation', required=True)

    # Stage Gating Rules
    require_document = fields.Boolean(
        string='Require Document / Checklist Upload',
        default=False,
        help='If checked, the technician/contractor cannot progress beyond this stage without uploading required paper/photos.'
    )
    required_doc_description = fields.Char(
        string='Required Document Instructions',
        help='Instructions for the technician/contractor on what must be uploaded (e.g., Shaft Alignment Form, Safety Certificate).'
    )

    # Contractor Milestone Billing
    can_bill_contractor = fields.Boolean(
        string='Allows Contractor Billing',
        default=False,
        help='Check if completing this stage allows generating an invoice/bill milestone for the external contractor.'
    )
    contractor_payment_percentage = fields.Float(
        string='Contractor Payment %',
        default=0.0,
        help='Percentage of contractor contract amount payable at this stage (e.g. 25%).'
    )

    is_closed = fields.Boolean(
        string='Closing / Completed Stage',
        default=False,
        help='Checked if this stage represents full completion of the work order.'
    )
    fold = fields.Boolean(
        string='Folded in Kanban',
        default=False
    )
