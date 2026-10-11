# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta

class ElevatorWorkOrder(models.Model):
    _name = 'elevator.work.order'
    _description = 'Elevator Work Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, date_planned_start desc, id desc'

    name = fields.Char(
        string='Work Order Ref',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent'),
        ('2', 'Emergency'),
    ], string='Priority', default='0', tracking=True)

    order_type = fields.Selection([
        ('installation', 'Elevator Installation (New Package)'),
        ('maintenance', 'Routine Maintenance / Inspection'),
        ('repair', 'Emergency Breakdown / Repair'),
    ], string='Work Order Type', default='installation', required=True, tracking=True)

    # Multi-Company Dimensions
    company_id = fields.Many2one(
        'res.company',
        string='Executing Company (Company B)',
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
        help='Company B: The technical entity that executes the physical installation and maintenance work.'
    )
    origin_company_id = fields.Many2one(
        'res.company',
        string='Sales Origin Company (Company A)',
        required=True,
        tracking=True,
        help='Company A: The sales company that contracted with the customer and subcontracted to Company B.'
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Origin Sale Order (Company A)',
        check_company=False,
        tracking=True,
        help='Sales contract from Company A selling the elevator package and service contract.'
    )
    contract_id = fields.Many2one(
        'elevator.contract',
        string='Related Service Contract',
        tracking=True,
        help='Linked maintenance or warranty contract.'
    )

    # Subcontract & Internal Revenue
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    subcontract_budget = fields.Monetary(
        string='Internal Subcontract Allocation',
        currency_field='currency_id',
        tracking=True,
        help='Internal value/revenue transferred from Company A to Company B (e.g. $15,000 USD).'
    )

    # Customer & Site Details
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer / Client',
        required=True,
        tracking=True
    )
    site_id = fields.Many2one(
        'elevator.site',
        string='Installation Site',
        required=True,
        tracking=True
    )
    elevator_unit_id = fields.Many2one(
        'elevator.unit',
        string='Elevator Unit / Serial',
        tracking=True
    )

    # Stages & Gating
    stage_id = fields.Many2one(
        'elevator.work.order.stage',
        string='Current Stage',
        tracking=True,
        group_expand='_read_group_stage_ids',
        copy=False
    )
    stage_sequence = fields.Integer(
        related='stage_id.sequence',
        string='Stage Sequence',
        store=True
    )
    stage_require_doc = fields.Boolean(
        related='stage_id.require_document',
        string='Current Stage Requires Document'
    )
    stage_doc_instructions = fields.Char(
        related='stage_id.required_doc_description',
        string='Required Document Instructions'
    )
    document_ids = fields.One2many(
        'elevator.work.order.document',
        'work_order_id',
        string='Checklists & Paperwork Uploads'
    )
    document_count = fields.Integer(
        string='Total Documents Uploaded',
        compute='_compute_document_count'
    )

    # Execution Team: Internal Technicians vs External Contractor
    contractor_type = fields.Selection([
        ('internal', 'Internal Technicians (Company B Staff)'),
        ('external', 'External Subcontractor / Contractor'),
    ], string='Assigned Execution Team', default='internal', required=True, tracking=True)

    technician_ids = fields.Many2many(
        'res.users',
        string='Internal Technicians',
        help='Technicians employed by Company B.'
    )
    contractor_id = fields.Many2one(
        'res.partner',
        string='External Contractor',
        tracking=True,
        domain="[('is_company', '=', True)]",
        help='Third-party installation contractor performing on-site labor.'
    )
    contractor_cost = fields.Monetary(
        string='Contractor Agreed Fee',
        currency_field='currency_id',
        tracking=True,
        help='Total agreed payment amount to the external contractor.'
    )
    contractor_bill_ids = fields.Many2many(
        'account.move',
        string='Contractor Vendor Bills',
        domain="[('move_type', '=', 'in_invoice')]",
        copy=False
    )
    contractor_bill_count = fields.Integer(
        string='Vendor Bills Count',
        compute='_compute_contractor_bill_count'
    )

    # Site Inventory & Material Requisition
    stock_picking_ids = fields.Many2many(
        'stock.picking',
        string='Site Delivery Orders (from Company A)',
        help='Deliveries sent to site by Company A awaiting Company B installation team.'
    )
    delivery_order_count = fields.Integer(
        string='Deliveries on Site Count',
        compute='_compute_delivery_order_count'
    )
    material_line_ids = fields.One2many(
        'elevator.work.order.material',
        'work_order_id',
        string='Materials Consumed on Site'
    )

    # Status & Dates
    state = fields.Selection([
        ('draft', 'Draft / Assigned'),
        ('in_progress', 'In Progress / On Site'),
        ('done', 'Completed & Handed Over'),
        ('cancelled', 'Cancelled'),
    ], string='Overall Status', default='draft', tracking=True)

    date_planned_start = fields.Datetime(string='Planned Start Date', tracking=True)
    date_planned_end = fields.Datetime(string='Planned Completion Date', tracking=True)
    date_completed = fields.Datetime(string='Actual Completion Date', readonly=True, tracking=True)

    notes = fields.Html(string='Work Order Instructions / Site Notes')

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('document_ids')
    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    @api.depends('contractor_bill_ids')
    def _compute_contractor_bill_count(self):
        for rec in self:
            rec.contractor_bill_count = len(rec.contractor_bill_ids)

    @api.depends('stock_picking_ids')
    def _compute_delivery_order_count(self):
        for rec in self:
            rec.delivery_order_count = len(rec.stock_picking_ids)

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        # Allow kanban columns to show all relevant stages
        return self.env['elevator.work.order.stage'].search([], order='sequence asc')

    # -------------------------------------------------------------------------
    # CRUD & CONSTRAINTS
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('elevator.work.order') or _('New')
            # Assign first stage by default if not set
            if not vals.get('stage_id'):
                order_type = vals.get('order_type', 'installation')
                stage = self.env['elevator.work.order.stage'].search([
                    ('stage_type', 'in', [order_type, 'all'])
                ], order='sequence asc', limit=1)
                if stage:
                    vals['stage_id'] = stage.id
        return super().create(vals_list)

    def write(self, vals):
        # Stage gating check
        if 'stage_id' in vals:
            target_stage = self.env['elevator.work.order.stage'].browse(vals['stage_id'])
            for rec in self:
                if rec.stage_id and rec.stage_id != target_stage:
                    rec._check_stage_progression_allowed(rec.stage_id, target_stage)
        return super().write(vals)

    def _check_stage_progression_allowed(self, current_stage, next_stage):
        """Validates that all mandatory paperwork is uploaded before advancing."""
        # Only gate if advancing forward
        if next_stage.sequence <= current_stage.sequence:
            return

        if current_stage.require_document:
            uploaded_docs = self.document_ids.filtered(lambda d: d.stage_id == current_stage)
            if not uploaded_docs:
                raise UserError(_(
                    "CANNOT PROCEED TO NEXT STAGE!\n\n"
                    "Stage '%(stage)s' has strict gating conditions.\n"
                    "You must upload the required document/checklist/paper before advancing.\n\n"
                    "Requirement: %(desc)s",
                    stage=current_stage.name,
                    desc=current_stage.required_doc_description or _("Required stage sign-off document")
                ))

    # -------------------------------------------------------------------------
    # ACTION BUTTONS & WORKFLOW
    # -------------------------------------------------------------------------
    def action_start(self):
        """Move work order into In Progress state."""
        for rec in self:
            rec.write({'state': 'in_progress'})
            rec.message_post(body=_("Work order has started on-site by Company B team."))

    def action_next_stage(self):
        """Advance to the next sequential stage with gating checks."""
        self.ensure_one()
        all_stages = self.env['elevator.work.order.stage'].search([
            ('stage_type', 'in', [self.order_type, 'all'])
        ], order='sequence asc')
        current_idx = list(all_stages.ids).index(self.stage_id.id) if self.stage_id.id in all_stages.ids else -1
        if current_idx >= 0 and current_idx + 1 < len(all_stages):
            next_stage = all_stages[current_idx + 1]
            # Write will trigger _check_stage_progression_allowed
            self.write({'stage_id': next_stage.id})
            if next_stage.is_closed:
                self.action_mark_done()
        else:
            if not self.stage_id.is_closed:
                self.action_mark_done()

    def action_mark_done(self):
        """Finalize the work order, update elevator unit, activate warranty contract, and notify Company A."""
        for rec in self:
            # Check all stages requiring documents have at least one upload
            gated_stages = self.env['elevator.work.order.stage'].search([
                ('stage_type', 'in', [rec.order_type, 'all']),
                ('require_document', '=', True)
            ])
            for stage in gated_stages:
                stage_docs = rec.document_ids.filtered(lambda d: d.stage_id == stage)
                if not stage_docs:
                    raise UserError(_(
                        "Cannot complete work order! Stage '%(stage)s' is missing mandatory paperwork.\n"
                        "Requirement: %(req)s",
                        stage=stage.name,
                        req=stage.required_doc_description or _("Verification paperwork")
                    ))

            rec.write({
                'state': 'done',
                'date_completed': fields.Datetime.now()
            })

            # Update Elevator Unit
            if rec.elevator_unit_id:
                if rec.order_type == 'installation':
                    today = fields.Date.today()
                    rec.elevator_unit_id.write({
                        'state': 'operational',
                        'installation_date': today,
                        'warranty_end_date': today + timedelta(days=365)
                    })
                else:
                    rec.elevator_unit_id.write({
                        'state': 'operational'
                    })

            # Activate or Create 1-Year Free Warranty Support Contract (Only for new installations)
            if rec.order_type == 'installation':
                rec._ensure_warranty_contract_created()

            # Notify Company A (Origin Sales Company)
            rec._notify_origin_sales_company()

    def _ensure_warranty_contract_created(self):
        """Creates or activates the 1-Year Free Service / Warranty Contract."""
        self.ensure_one()
        if not self.contract_id and self.order_type == 'installation':
            today = fields.Date.today()
            contract = self.env['elevator.contract'].create({
                'partner_id': self.partner_id.id,
                'site_id': self.site_id.id,
                'elevator_unit_id': self.elevator_unit_id.id if self.elevator_unit_id else False,
                'sale_order_id': self.sale_order_id.id if self.sale_order_id else False,
                'origin_company_id': self.origin_company_id.id,
                'company_id': self.company_id.id,
                'contract_type': 'warranty',
                'date_start': today,
                'date_end': today + timedelta(days=365),
                'visit_interval_months': 1,
                'state': 'active',
            })
            self.contract_id = contract.id
            self.message_post(body=_(
                "1-Year Free Warranty Service Contract <b>%(contract)s</b> has been generated and activated.",
                contract=contract.name
            ))

    def _notify_origin_sales_company(self):
        """Sends completion notification back to Company A sale order chatter and updates state."""
        self.ensure_one()
        if self.sale_order_id:
            if self.order_type == 'repair':
                msg = _(
                    "🔧 <b>PAID ELEVATOR REPAIR &amp; PARTS REPLACEMENT COMPLETED ON SITE</b><br/>"
                    "• <b>Work Order:</b> %(wo)s<br/>"
                    "• <b>Executing Company:</b> %(exec_comp)s<br/>"
                    "• <b>Site:</b> %(site)s<br/>"
                    "• <b>Elevator Asset:</b> %(unit)s<br/>"
                    "• <b>Completion Date:</b> %(date)s<br/>"
                    "• <b>Customer Sign-off:</b> VALIDATED &amp; SIGNED<br/>"
                    "Replacement spare parts have been installed, tested, and accepted by customer.",
                    wo=self.name,
                    exec_comp=self.company_id.name,
                    site=self.site_id.name,
                    unit=self.elevator_unit_id.name if self.elevator_unit_id else _("Standard"),
                    date=fields.Date.today()
                )
            else:
                msg = _(
                    "🎉 <b>ELEVATOR INSTALLATION COMPLETED ON SITE</b><br/>"
                    "• <b>Work Order:</b> %(wo)s<br/>"
                    "• <b>Executing Company:</b> %(exec_comp)s<br/>"
                    "• <b>Site:</b> %(site)s<br/>"
                    "• <b>Unit:</b> %(unit)s<br/>"
                    "• <b>Completion Date:</b> %(date)s<br/>"
                    "• <b>1-Year Free Warranty Support:</b> ACTIVE (Valid until %(warranty_end)s)<br/>"
                    "All installation stages, safety drop test reports, and handover certificates have been officially validated.",
                    wo=self.name,
                    exec_comp=self.company_id.name,
                    site=self.site_id.name,
                    unit=self.elevator_unit_id.name if self.elevator_unit_id else _("Standard"),
                    date=fields.Date.today(),
                    warranty_end=fields.Date.today() + timedelta(days=365)
                )
            # Post chatter in Company A's Sale Order
            self.sale_order_id.message_post(body=msg)
            self.sale_order_id.elevator_installation_state = 'completed'

    # -------------------------------------------------------------------------
    # CONTRACTOR BILLING (VENDOR BILL)
    # -------------------------------------------------------------------------
    def action_create_contractor_bill(self):
        """Creates a Vendor Bill for the external contractor in Company B."""
        self.ensure_one()
        if self.contractor_type != 'external':
            raise UserError(_("This work order is assigned to Internal Technicians. Vendor Bills are only generated for External Contractors."))
        if not self.contractor_id:
            raise UserError(_("Please specify an External Contractor first."))
        if self.contractor_cost <= 0:
            raise UserError(_("Please specify a valid Contractor Fee amount before generating a bill."))

        # Verify that required paperwork for current stage exists
        if self.stage_id.require_document:
            stage_docs = self.document_ids.filtered(lambda d: d.stage_id == self.stage_id)
            if not stage_docs:
                raise UserError(_(
                    "Contractor payment cannot be processed yet!\n"
                    "Mandatory papers/checklists for stage '%(stage)s' have not been uploaded by the contractor.\n"
                    "Required: %(desc)s",
                    stage=self.stage_id.name,
                    desc=self.stage_id.required_doc_description or _("Work completion papers")
                ))

        # Check existing bills
        existing_draft = self.contractor_bill_ids.filtered(lambda b: b.state == 'draft')
        if existing_draft:
            raise UserError(_("There is already a draft Vendor Bill (%s) for this contractor on this Work Order.", existing_draft[0].name))

        # Label: Work Order and Contractor Name
        stage_title = self.stage_id.name if self.stage_id else _('General')
        bill_label = f"WO: {self.name} - Stage: {stage_title} - Contractor: {self.contractor_id.name}"

        # Create Vendor Bill in Company B
        move_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.contractor_id.id,
            'company_id': self.company_id.id,
            'invoice_date': fields.Date.today(),
            'ref': bill_label,
            'invoice_line_ids': [
                (0, 0, {
                    'name': f"Subcontracted Elevator Installation Service - {bill_label}",
                    'quantity': 1.0,
                    'price_unit': self.contractor_cost,
                })
            ]
        }
        bill = self.env['account.move'].with_company(self.company_id).create(move_vals)
        self.contractor_bill_ids = [(4, bill.id)]

        self.message_post(
            body=_("Vendor Bill <b><a href=# data-oe-model=account.move data-oe-id=%(bill_id)s>%(bill_ref)s</a></b> has been created for external contractor %(contractor)s.",
                   bill_id=bill.id,
                   bill_ref=bill.name or bill.ref,
                   contractor=self.contractor_id.name)
        )

        return {
            'name': _('Contractor Vendor Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': bill.id,
            'view_mode': 'form',
        }

    def action_view_contractor_bills(self):
        self.ensure_one()
        return {
            'name': _('Contractor Vendor Bills for %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.contractor_bill_ids.ids)],
            'context': {'default_move_type': 'in_invoice', 'default_company_id': self.company_id.id},
        }

    def action_view_site_deliveries(self):
        self.ensure_one()
        return {
            'name': _('Site Deliveries from Company A'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.stock_picking_ids.ids)],
        }

    def action_upload_paperwork(self):
        self.ensure_one()
        return {
            'name': _('Upload Stage Paperwork / Checklist'),
            'type': 'ir.actions.act_window',
            'res_model': 'elevator.work.order.document',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_work_order_id': self.id,
                'default_stage_id': self.stage_id.id if self.stage_id else False,
            }
        }


class ElevatorWorkOrderMaterial(models.Model):
    _name = 'elevator.work.order.material'
    _description = 'Elevator Work Order Consumed Material'

    work_order_id = fields.Many2one(
        'elevator.work.order',
        string='Work Order',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Spare Part / Component',
        required=True
    )
    quantity = fields.Float(string='Quantity Used', default=1.0)
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        readonly=True
    )
    source_location = fields.Selection([
        ('site_inventory', 'Used from Site Inventory (Company A Delivery)'),
        ('company_a_storage', 'Requested from Company A Central Storage'),
        ('company_b_storage', 'Taken from Company B Van/Storage'),
    ], string='Material Source', default='site_inventory', required=True)
    notes = fields.Char(string='Notes / Serial No.')
