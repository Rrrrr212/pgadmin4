##########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2026, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

"""Implements Database Document Generator feature."""

from flask import request
from flask_babel import gettext
from pgadmin.user_login_check import pga_login_required

from pgadmin.utils import PgAdminModule
from pgadmin.utils.ajax import make_json_response, bad_request, internal_server_error
from pgadmin.tools.docgen.engine import DocGenEngine

MODULE_NAME = 'docgen'


class DocGenModule(PgAdminModule):
    LABEL = gettext('Database Document Generator')

    def get_own_menuitems(self):
        return {'tools': [
            {
                'name': 'mnu_docgen',
                'label': gettext('Database Document Generator'),
                'priority': 150,
                'icon': 'fa fa-file-text',
                'url': '/tools/docgen'
            }
        ]}

    def get_exposed_url_endpoints(self):
        return [
            'docgen.index',
            'docgen.generate',
            'docgen.preview',
            'docgen.get_databases',
        ]


blueprint = DocGenModule(MODULE_NAME, __name__, static_url_path='/static')


@blueprint.route('/', endpoint='index')
@pga_login_required
def index():
    return bad_request(errormsg=gettext("This URL cannot be called directly."))


@blueprint.route('/generate/<int:sid>/<int:did>', methods=['POST'], endpoint='generate')
@pga_login_required
def generate(sid, did):
    data = request.get_json() if request.is_json else {}
    include_tables = data.get('include_tables', True)
    include_views = data.get('include_views', True)
    include_functions = data.get('include_functions', False)
    include_sequences = data.get('include_sequences', False)
    output_format = data.get('output_format', 'markdown')

    engine = DocGenEngine(sid, did)

    try:
        doc_content = engine.generate_document(
            include_tables=include_tables,
            include_views=include_views,
            include_functions=include_functions,
            include_sequences=include_sequences,
            output_format=output_format
        )
        return make_json_response(
            success=1,
            data={
                'content': doc_content,
                'format': output_format
            }
        )
    except Exception as e:
        return internal_server_error(errormsg=str(e))


@blueprint.route('/preview/<int:sid>/<int:did>', methods=['POST'], endpoint='preview')
@pga_login_required
def preview(sid, did):
    data = request.get_json() if request.is_json else {}
    include_tables = data.get('include_tables', True)
    include_views = data.get('include_views', True)
    include_functions = data.get('include_functions', False)
    include_sequences = data.get('include_sequences', False)

    engine = DocGenEngine(sid, did)

    try:
        doc_content = engine.generate_document(
            include_tables=include_tables,
            include_views=include_views,
            include_functions=include_functions,
            include_sequences=include_sequences,
            output_format='markdown'
        )
        return make_json_response(
            success=1,
            data={'content': doc_content}
        )
    except Exception as e:
        return internal_server_error(errormsg=str(e))


@blueprint.route('/databases/<int:sid>', endpoint='get_databases')
@pga_login_required
def get_databases(sid):
    from pgadmin.utils.driver import get_driver
    from config import PG_DEFAULT_DRIVER

    try:
        manager = get_driver(PG_DEFAULT_DRIVER).connection_manager(sid)
        conn = manager.connection()
        status, msg = conn.connect()
        if not status:
            return internal_server_error(errormsg=msg)

        sql = """
            SELECT datname as name, pg_catalog.pg_get_userbyid(datdba) as owner
            FROM pg_catalog.pg_database
            WHERE datistemplate = false
            ORDER BY datname;
        """
        status, result = conn.execute_dict(sql)
        if not status:
            return internal_server_error(errormsg=result)

        return make_json_response(
            success=1,
            data=result.get('rows', [])
        )
    except Exception as e:
        return internal_server_error(errormsg=str(e))
