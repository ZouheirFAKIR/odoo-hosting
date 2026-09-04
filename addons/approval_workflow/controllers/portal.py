# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class ApprovalPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'approval_count' in counters:
            employee = request.env.user.employee_id
            values['approval_count'] = request.env['approval.request'].search_count([
                ('employee_id', '=', employee.id),
            ]) if employee else 0
        return values

    @http.route(['/my/approval_requests', '/my/approval_requests/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_my_approval_requests(self, page=1, **kw):
        employee = request.env.user.employee_id
        domain = [('employee_id', '=', employee.id)] if employee else [('id', '=', 0)]

        Request = request.env['approval.request']
        total = Request.search_count(domain)
        pager = portal_pager(
            url="/my/approval_requests",
            total=total,
            page=page,
            step=20,
        )
        requests = Request.search(
            domain, limit=20, offset=pager['offset'], order='create_date desc',
        )
        return request.render('approval_workflow.portal_my_approval_requests', {
            'requests': requests,
            'pager': pager,
            'page_name': 'approval_request',
        })

    @http.route(['/my/approval_requests/<int:request_id>'], type='http', auth='user', website=True)
    def portal_approval_request_detail(self, request_id, **kw):
        approval_request = request.env['approval.request'].browse(request_id)
        employee = request.env.user.employee_id
        if not approval_request.exists() or approval_request.employee_id != employee:
            return request.redirect('/my/approval_requests')
        return request.render('approval_workflow.portal_approval_request_detail', {
            'approval_request': approval_request,
        })