# -*- coding: utf-8 -*-
import logging
import pprint
import werkzeug

from openerp import http, SUPERUSER_ID
from openerp.http import request

_logger = logging.getLogger(__name__)


class RedsysController(http.Controller):
    _return_url = '/payment/redsys/return'
    _cancel_url = '/payment/redsys/cancel'
    _exception_url = '/payment/redsys/error'
    _reject_url = '/payment/redsys/reject'

    @http.route([
        '/payment/redsys/return',
        '/payment/redsys/cancel',
        '/payment/redsys/error',
        '/payment/redsys/reject',
    ], type='http', auth='none')
    def redsys_return(self, **post):
        """ Redsys."""
        _logger.info('Redsys: entering form_feedback with post data %s',
                     pprint.pformat(post))  # debug
        request.registry['payment.transaction'].form_feedback(
            request.cr, SUPERUSER_ID, post, 'redsys',
            context=request.context)
        return_url = post.pop('return_url', '')
        if not return_url:
            return_url = 'http://localhost:8069/page/gracias-por-su-compra'
        return werkzeug.utils.redirect(return_url)
