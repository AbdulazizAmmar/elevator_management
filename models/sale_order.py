# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_elevator_package = fields.Boolean(
        string='Elevator Package & Installation',
        default=False,
        tracking=True,
        help='Check if this sales order includes elevator equipment, installation, and 1-year free service.'
    )
    elevator_site_id = fields.Many2one(
        'elevator.site',
        string='Installation Site',
        tracking=True,
        domain="[('partner_id', '=', partner_id)]",
        help='Customer site or building where the elevator will be installed.'
    )
    elevator_unit_model = fields.Char(
        string='Elevator Model / Package',
        help='e.g., SkyLine Panoramic 8-Passenger 630kg'
    )
    elevator_unit_id = fields.Many2one(
        'elevator.unit',
        string='Elevator Unit Asset',
        check_company=False,
        tracking=True
    )

    # Subcontract to Operations Company (Company B)
    subcontract_company_id = fields.Many2one(
        'res.company',
        string='Subcontract Operations Company (Company B)',
        tracking=True,
        help='The technical company entity that executes physical installation and maintenance (Company B).'
    )
    subcontract_budget = fields.Monetary(
        string='Subcontract Value (Company B Allocation)',
        currency_field='currency_id',
        tracking=True,
        help='Internal value/revenue allocated to Company B for execution (e.g., $15,000 USD).'
    )
    elevator_work_order_id = fields.Many2one(
        'elevator.work.order',
        string='Assigned Work Order (Company B)',
        check_company=False,
        readonly=True,
        tracking=True
    )
    elevator_installation_state = fields.Selection([
        ('not_applicable', 'Not Applicable'),
        ('pending_subcontract', 'Pending Subcontract to Company B'),
        ('subcontracted', 'Installation In Progress (Company B)'),
        ('completed', 'Installed & Operational'),
    ], string='Elevator Job Progress', default='not_applicable', tracking=True)

    elevator_contract_id = fields.Many2one(
        'elevator.contract',
        string='1-Year Free Service / Warranty Contract',
        check_company=False,
        readonly=True,
        tracking=True
    )

    elevator_job_type = fields.Selection([
        ('installation', 'New Elevator Package (Installation + 1-Yr Free Warranty)'),
        ('repair', 'Paid Repair / Spare Parts Replacement'),
    ], string='Elevator Job Category', default='installation', tracking=True)

    @api.onchange('elevator_unit_id')
    def _onchange_elevator_unit_id(self):
        if self.elevator_unit_id and self.elevator_unit_id.site_id:
            self.elevator_site_id = self.elevator_unit_id.site_id

    @api.onchange('is_elevator_package', 'elevator_job_type')
    def _onchange_is_elevator_package(self):
        if self.is_elevator_package and self.elevator_installation_state == 'not_applicable':
            self.elevator_installation_state = 'pending_subcontract'
            # Suggest default subcontract budget if total is set
            if self.amount_total and not self.subcontract_budget:
                rate = 0.75 if self.elevator_job_type == 'installation' else 0.40
                self.subcontract_budget = self.amount_total * rate

    def action_subcontract_to_company_b(self):
        """Creates the Work Order directly in Company B without generating a redundant sales order."""
        self.ensure_one()
        if not self.subcontract_company_id:
            raise UserError(_("Please select the Subcontract Operations Company (Company B)."))

        # GATHER SPARE PARTS ORDERED (For Repair Jobs)
        material_vals = []
        if self.elevator_job_type == 'repair':
            if not self.elevator_unit_id:
                raise UserError(_("For repair and spare parts replacement, please select the target Elevator Unit Asset."))
            if not self.elevator_site_id and self.elevator_unit_id.site_id:
                self.elevator_site_id = self.elevator_unit_id.site_id

            # Extract spare parts from SO lines
            for line in self.order_line:
                if line.product_id and line.product_id.type != 'service':
                    material_vals.append((0, 0, {
                        'product_id': line.product_id.id,
                        'quantity': line.product_uom_qty,
                        'source_location': 'site_inventory',
                        'notes': _("Replacement part from SO %(so)s (%(desc)s)", so=self.name, desc=line.name),
                    }))

        if not self.elevator_site_id:
            raise UserError(_("Please select an Installation Site for the customer before subcontracting."))

        # 1. Create or link Elevator Unit asset (if installation)
        if self.elevator_job_type == 'installation' and not self.elevator_unit_id:
            unit = self.env['elevator.unit'].create({
                'model_name': self.elevator_unit_model or _('Elevator Package'),
                'partner_id': self.partner_id.id,
                'site_id': self.elevator_site_id.id,
                'company_id': self.subcontract_company_id.id,
                'origin_company_id': self.company_id.id,
                'sale_order_id': self.id,
                'state': 'installation',
            })
            self.elevator_unit_id = unit.id

        # 2. Gather site delivery stock pickings from Company A
        site_pickings = self.picking_ids

        # 3. Create Elevator Work Order in Company B
        order_type = 'repair' if self.elevator_job_type == 'repair' else 'installation'
        notes_html = _(
            "<b>%(job_type)s</b> subcontracted from Sales Order <b>%(so)s</b> (Company: %(so_comp)s).<br/>"
            "Total Invoiced to Customer: %(so_amount)s | Subcontract Allocation to Company B: %(sub_budget)s.<br/>"
            "Parts delivered/dispatched from %(so_comp)s to site.",
            job_type=_("Paid Repair & Parts Replacement") if order_type == 'repair' else _("New Elevator Package Installation"),
            so=self.name,
            so_comp=self.company_id.name,
            so_amount=f"{self.amount_total} {self.currency_id.symbol or ''}",
            sub_budget=f"{self.subcontract_budget} {self.currency_id.symbol or ''}"
        )

        wo_vals = {
            'order_type': order_type,
            'partner_id': self.partner_id.id,
            'site_id': self.elevator_site_id.id,
            'elevator_unit_id': self.elevator_unit_id.id if self.elevator_unit_id else False,
            'sale_order_id': self.id,
            'origin_company_id': self.company_id.id,
            'company_id': self.subcontract_company_id.id,
            'currency_id': self.currency_id.id,
            'subcontract_budget': self.subcontract_budget,
            'stock_picking_ids': [(6, 0, site_pickings.ids)],
            'material_line_ids': material_vals,
            'notes': notes_html
        }
        work_order = self.env['elevator.work.order'].with_company(self.subcontract_company_id).create(wo_vals)

        # 4. Link picking records to this work order
        for picking in site_pickings:
            picking.elevator_work_order_id = work_order.id
            picking.elevator_site_id = self.elevator_site_id.id

        # 5. Update Sale Order state
        self.write({
            'elevator_work_order_id': work_order.id,
            'elevator_installation_state': 'subcontracted'
        })

        self.message_post(body=_(
            "Subcontracted %(job)s job to <b>%(comp_b)s</b>.<br/>"
            "• Work Order: <b><a href=# data-oe-model=elevator.work.order data-oe-id=%(wo_id)s>%(wo_name)s</a></b><br/>"
            "• Internal Allocation Value: %(budget)s %(curr)s<br/>"
            "Company B technical team is now dispatched to site.",
            job=_("Repair & Parts Replacement") if order_type == 'repair' else _("Installation"),
            comp_b=self.subcontract_company_id.name,
            wo_id=work_order.id,
            wo_name=work_order.name,
            budget=self.subcontract_budget,
            curr=self.currency_id.name
        ))

        return {
            'name': _('Elevator Work Order (Company B)'),
            'type': 'ir.actions.act_window',
            'res_model': 'elevator.work.order',
            'res_id': work_order.id,
            'view_mode': 'form',
        }

    def action_view_elevator_work_order(self):
        self.ensure_one()
        if not self.elevator_work_order_id:
            raise UserError(_("No work order has been created yet."))
        return {
            'name': _('Elevator Work Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'elevator.work.order',
            'res_id': self.elevator_work_order_id.id,
            'view_mode': 'form',
        }

    def action_view_elevator_contract(self):
        self.ensure_one()
        contract = self.elevator_contract_id or self.elevator_work_order_id.contract_id
        if not contract:
            raise UserError(_("No 1-year service contract has been activated yet."))
        return {
            'name': _('Elevator Service Contract'),
            'type': 'ir.actions.act_window',
            'res_model': 'elevator.contract',
            'res_id': contract.id,
            'view_mode': 'form',
        }
