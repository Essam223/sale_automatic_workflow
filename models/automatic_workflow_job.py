# Copyright 2011 Akretion Sébastien BEAU <sebastien.beau@akretion.com>
# Copyright 2013 Camptocamp SA (author: Guewen Baconnier)
# Copyright 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from contextlib import contextmanager
from odoo import api, models
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


@contextmanager
def savepoint(cr):
    """ Open a savepoint on the cursor, then yield.

    Warning: using this method, the exceptions are logged then discarded.
    """
    try:
        with cr.savepoint():
            yield
    except Exception:
        _logger.exception('Error during an automatic workflow action.')


@contextmanager
def force_company(env, company_id):
    user_company = env.user.company_id
    env.user.update({'company_id': company_id})
    try:
        yield
    finally:
        env.user.update({'company_id': user_company})


class AutomaticWorkflowJob(models.Model):
    """ Scheduler that will play automatically the validation of
    invoices, pickings...  """

    _name = 'automatic.workflow.job'
    _description = (
        'Scheduler that will play automatically the validation of'
        ' invoices, pickings...'
    )

    @api.model
    def _validate_sale_orders(self, order_filter):
        print(order_filter)
        sale_obj = self.env['sale.order']
        sales = sale_obj.search(order_filter)
        _logger.debug('Sale Orders to validate: %s', sales.ids)
        for sale in sales:
            with savepoint(self.env.cr), force_company(self.env,
                                                       sale.company_id):
                sale.action_confirm()

    @api.model
    def _create_invoices(self, create_filter):
        sale_obj = self.env['sale.order']
        sales = sale_obj.search(create_filter)
        _logger.debug('Sale Orders to create Invoice: %s', sales.ids)
        for sale in sales:
            with savepoint(self.env.cr), force_company(self.env,
                                                       sale.company_id):
                payment = self.env['sale.advance.payment.inv'].create(
                    {'advance_payment_method': 'all'})
                payment.with_context(active_ids=sale.ids).create_invoices()

    @api.model
    def _validate_invoices(self, validate_invoice_filter):
        invoice_obj = self.env['account.invoice']
        invoices = invoice_obj.search(validate_invoice_filter)
        _logger.debug('Invoices to validate: %s', invoices.ids)
        for invoice in invoices:
            with savepoint(self.env.cr), force_company(self.env,
                                                       invoice.company_id):
                # FIX Why is this needed for certain invoices
                # in enterprise in multicompany?
                invoice.with_context(
                    force_company=invoice.company_id.id).action_invoice_open()

    @api.model
    def _validate_pickings(self, picking_filter):
        picking_obj = self.env['stock.picking']
        pickings = picking_obj.search(picking_filter)
        _logger.debug('Pickings to validate: %s', pickings.ids)
        for picking in pickings:
            with savepoint(self.env.cr):
                picking.validate_picking()

    @api.model
    def _sale_done(self, sale_done_filter):
        sale_obj = self.env['sale.order']
        sales = sale_obj.search(sale_done_filter)
        _logger.debug('Sale Orders to done: %s', sales.ids)
        for sale in sales:
            with savepoint(self.env.cr), force_company(self.env,
                                                       sale.company_id):
                sale.action_done()

    @api.model
    def run_with_workflow(self, sale_workflow):
        print("i am inside run with workflow")
        # print("order_filter_id : ",sale_workflow.order_filter_id.domain)
        workflow_domain = [('workflow_process_id', '=', sale_workflow.id)]
        # print("workflow_domain : ", workflow_domain)
        if sale_workflow.validate_order:
            self._validate_sale_orders(sale_workflow,
                safe_eval(sale_workflow.order_filter_id.domain) +
                workflow_domain)
        if sale_workflow.validate_picking:
            self._validate_pickings(sale_workflow,
                safe_eval(sale_workflow.picking_filter_id.domain) +
                workflow_domain)
        if sale_workflow.create_invoice:
            self._create_invoices(sale_workflow,
                safe_eval(sale_workflow.create_invoice_filter_id.domain) +
                workflow_domain)
        if sale_workflow.validate_invoice:
            self._validate_invoices(sale_workflow,
                safe_eval(
                    sale_workflow.validate_invoice_filter_id.domain) +
                workflow_domain)
        if sale_workflow.sale_done:
            self._sale_done(sale_workflow,
                safe_eval(
                    sale_workflow.sale_done_filter_id.domain) +
                workflow_domain)

    @api.model
    def run(self):
        # print("i am inside run")
        """ Must be called from ir.cron """
        sale_workflow_process = self.env['sale.workflow.process']
        print(sale_workflow_process)
        for sale_workflow in sale_workflow_process.search([]):
            self.run_with_workflow(sale_workflow)
        return True


class ActionConfirm(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        #confirm order
        super(ActionConfirm, self).action_confirm()
        # auto delivery order
        picking_obj = self.env['stock.picking']
        pickings = picking_obj.search([('sale_id', '=', self.id)])
        print('Pickings to validate: %s', pickings.ids)
        for picking in pickings:
            with savepoint(self.env.cr):
                picking.validate_picking()
        # auto create invoice
        sale_obj = self.env['sale.order']
        sales = sale_obj.search([('id', '=', self.id)])
        print('Sale Orders to create Invoice: %s', sales.ids)
        for sale in sales:
            with savepoint(self.env.cr), force_company(self.env,
                                                       sale.company_id):
                payment = self.env['sale.advance.payment.inv'].create(
                    {'advance_payment_method': 'all'})
                payment.with_context(active_ids=sale.ids).create_invoices()

        # auto validate invoice
        invoice_obj = self.env['account.invoice']
        print([('origin', '=', self.name)])
        invoices = invoice_obj.search([('origin', '=', self.name)])
        print('Invoices to validate: %s', invoices.ids)
        for invoice in invoices:
            with savepoint(self.env.cr), force_company(self.env,
                                                       invoice.company_id):
                invoice.with_context(
                    force_company=invoice.company_id.id).action_invoice_open()

        # print('I am here')
        # print(self.workflow_process_id)
        # AutomaticWorkflowJob.run_with_workflow(AutomaticWorkflowJob,self.workflow_process_id)
        # return super(ActionConfirm, self).action_confirm()

