# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ElevatorWorkOrderDocument(models.Model):
    _name = 'elevator.work.order.document'
    _description = 'Elevator Work Order Uploaded Document & Checklist'
    _order = 'upload_date desc, id desc'

    name = fields.Char(string='Document Title', required=True)
    work_order_id = fields.Many2one(
        'elevator.work.order',
        string='Work Order',
        required=True,
        ondelete='cascade'
    )
    stage_id = fields.Many2one(
        'elevator.work.order.stage',
        string='Associated Stage',
        required=True
    )
    file = fields.Binary(
        string='File / Paper Scan / Photo',
        required=True,
        attachment=True
    )
    file_name = fields.Char(string='File Name')
    document_type = fields.Selection([
        ('site_inspection', 'Site Readiness & Shaft Check Sheet'),
        ('mechanical_check', 'Guide Rails & Mechanical Alignment Report'),
        ('electrical_check', 'Wiring, Control Panel & Motor Test'),
        ('safety_certificate', 'Safety Gear Drop Test & Brake Certificate'),
        ('handover_signed', 'Customer Signed Handover & Acceptance Form'),
        ('contractor_completion', 'Contractor Work Completion Form'),
        ('photo_evidence', 'On-Site Progress Photo Evidence'),
        ('other', 'Other Paperwork / Document'),
    ], string='Document Category', default='site_inspection', required=True)

    uploaded_by = fields.Many2one(
        'res.users',
        string='Uploaded By',
        default=lambda self: self.env.user,
        readonly=True
    )
    upload_date = fields.Datetime(
        string='Uploaded On',
        default=fields.Datetime.now,
        readonly=True
    )
    is_approved = fields.Boolean(
        string='Approved by Supervisor',
        default=False,
        help='Supervisor signs off on this document/photo before stage completion.'
    )
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True
    )
    notes = fields.Text(string='Inspector Notes / Comments')

    def action_approve(self):
        self.ensure_one()
        self.write({
            'is_approved': True,
            'approved_by': self.env.user.id
        })
        self.work_order_id.message_post(
            body=_("Document '%(doc)s' for stage '%(stage)s' was approved by %(user)s.",
                   doc=self.name,
                   stage=self.stage_id.name,
                   user=self.env.user.name)
        )
