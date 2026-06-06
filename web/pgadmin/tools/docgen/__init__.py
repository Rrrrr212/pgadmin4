##########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2026, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

"""A blueprint module implementing the database documentation generator."""
import json

from flask import request, session
from flask_babel import gettext
from flask_security import permissions_required
from pgadmin.user_login_check import pga_login_required
from pgadmin.utils import PgAdminModule
from pgadmin.utils.ajax import make_json_response, internal_server_error
from pgadmin.utils.driver import get_driver
from pgadmin.utils.exception import ConnectionLost
from config import PG_DEFAULT_DRIVER, ALLOW_SAVE_PASSWORD
from pgadmin.tools.user_management.PgAdminPermissions import AllPermissionTypes

from .engine import DocGenEngine

MODULE_NAME = 'docgen'


class DocGenModule(PgAdminModule):
    """
    class DocGenModule(PgAdminModule)

        A module class for Database Documentation Generator
        derived from PgAdminModule.
    """

    LABEL = gettext("Database Documentation Generator")

    def get_own_menuitems(self):
        return {}

    def get_exposed_url_endpoints(self):
        return [
            'docgen.generate',
        ]


blueprint = DocGenModule(MODULE_NAME, __name__, static_url_path='/static')


def _get_connection(sid, did, trans_id):
    manager = get_driver(PG_DEFAULT_DRIVER).connection_manager(sid)
    try:
        conn = manager.connection(
            conn_id=trans_id,
            auto_reconnect=True,
            use_binary_placeholder=True,
            did=did
        )
        status, msg = conn.connect()
        if not status:
            from flask import current_app
            current_app.logger.error(msg)
            raise ConnectionLost(sid, conn.db, trans_id)

        return conn
    except Exception as e:
        from flask import current_app
        current_app.logger.error(e)
        raise


@blueprint.route(
    '/generate/<int:sid>/<int:did>',
    methods=["POST"],
    endpoint='generate'
)
@permissions_required(AllPermissionTypes.tools_docgen)
@pga_login_required
def generate(sid, did):
    data = {}
    if request.data:
        data = json.loads(request.data)

    trans_id = data.get('trans_id', session.get('docgen_trans_id'))

    try:
        conn = _get_connection(sid, did, trans_id)
    except ConnectionLost as e:
        return make_json_response(
            success=0,
            status=428,
            result={
                "errmsg": str(e),
                "prompt_password": True,
                "allow_save_password": True
                if ALLOW_SAVE_PASSWORD and
                session.get('allow_save_password', None) else False,
            }
        )
    except Exception as e:
        return internal_server_error(errormsg=str(e))

    output_format = data.get('format', 'markdown')
    include_tables = data.get('include_tables', True)
    include_views = data.get('include_views', True)
    include_functions = data.get('include_functions', True)
    schema_filter = data.get('schema', None)

    engine = DocGenEngine(conn)

    try:
        doc_content = engine.generate(
            output_format=output_format,
            include_tables=include_tables,
            include_views=include_views,
            include_functions=include_functions,
            schema_filter=schema_filter,
        )
    except Exception as e:
        from flask import current_app
        current_app.logger.error(e)
        return internal_server_error(errormsg=str(e))

    return make_json_response(
        data={
            'content': doc_content,
            'database': conn.db,
            'format': output_format,
        }
    )