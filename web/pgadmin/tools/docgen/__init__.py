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

from flask import request, render_template, send_file
from flask_security import permissions_required
from pgadmin.user_login_check import pga_login_required
from flask_babel import gettext
from pgadmin.utils import PgAdminModule
from pgadmin.utils.ajax import make_json_response, internal_server_error, bad_request
from pgadmin.utils.driver import get_driver
from pgadmin.utils.server_access import get_server
from pgadmin.model import Server
from config import PG_DEFAULT_DRIVER, ALLOW_SAVE_PASSWORD
from pgadmin.tools.docgen.engine import DocGenEngine
from pgadmin.tools.user_management.PgAdminPermissions import AllPermissionTypes
from pgadmin.browser.server_groups.servers.utils import convert_connection_parameter

MODULE_NAME = 'docgen'


class DocGenModule(PgAdminModule):
    """
    A module class for Database Documentation Generator derived from PgAdminModule.
    """

    LABEL = gettext("Database Documentation Generator")

    def get_own_menuitems(self):
        return {'tools': [
            {
                'name': 'mnu_docgen',
                'label': gettext('Database Documentation Generator'),
                'icon': 'fa fa-file-text',
                'url': ''
            }
        ]}

    def get_exposed_url_endpoints(self):
        """
        Returns:
            list: URL endpoints for docgen module
        """
        return [
            'docgen.index',
            'docgen.panel',
            'docgen.initialize',
            'docgen.generate',
            'docgen.download',
        ]


blueprint = DocGenModule(MODULE_NAME, __name__, static_url_path='/static')


@blueprint.route('/')
@pga_login_required
def index():
    return bad_request(
        errormsg=gettext('This URL cannot be requested directly.')
    )


@blueprint.route(
    '/panel/<int:trans_id>',
    methods=["POST"],
    endpoint='panel'
)
@permissions_required(AllPermissionTypes.tools_query_tool)
@pga_login_required
def panel(trans_id):
    """
    This method renders the documentation generator panel.

    Args:
        trans_id: unique transaction id
    """
    params = {'trans_id': trans_id}
    if request.form:
        for key, val in request.form.items():
            params[key] = val

    if request.args:
        params.update({k: v for k, v in request.args.items()})

    s = get_server(int(params['sid']))
    if s:
        params['bgcolor'] = s.bgcolor
        params['fgcolor'] = s.fgcolor or 'black'
        params['server_name'] = s.name

        return render_template(
            "docgen/index.html",
            title=gettext('Database Documentation Generator'),
            params=json.dumps(params),
        )
    else:
        params['error'] = 'The server was not found.'
        return render_template(
            "docgen/index.html",
            title=None,
            params=json.dumps(params))


@blueprint.route(
    '/initialize/<int:trans_id>/<int:sgid>/<int:sid>/<int:did>',
    methods=["POST"],
    endpoint='initialize'
)
@pga_login_required
def initialize(trans_id, sgid, sid, did):
    """
    Initialize the documentation generator and establish connection.

    Args:
        trans_id: Transaction ID
        sgid: Server group ID
        sid: Server ID
        did: Database ID
    """
    data = {}
    if request.data:
        data = json.loads(request.data)

    kwargs = {
        'user': data.get('user'),
        'role': data.get('role'),
        'password': data.get('password')
    }

    server = get_server(sid)
    if server is None:
        return make_json_response(
            status=410, success=0,
            errormsg=gettext("Could not find the required server.")
        )

    if kwargs.get('password') is None:
        kwargs['encpass'] = server.password
    else:
        kwargs['encpass'] = None

    try:
        manager = get_driver(PG_DEFAULT_DRIVER).connection_manager(sid)
        conn = manager.connection(
            conn_id=trans_id,
            auto_reconnect=True,
            use_binary_placeholder=True,
            did=did
        )

        if kwargs.get('user'):
            status, msg = conn.connect(
                user=kwargs['user'],
                role=kwargs.get('role'),
                password=kwargs['password'],
                encpass=kwargs['encpass']
            )
        else:
            status, msg = conn.connect()

        if not status:
            return make_json_response(
                success=0,
                status=428,
                result={
                    "server_label": server.name,
                    "username": kwargs.get('user') or server.username,
                    "errmsg": msg,
                    "prompt_password": True,
                    "allow_save_password": True
                    if ALLOW_SAVE_PASSWORD and
                    __import__('flask', fromlist=['session']).session.get(
                        'allow_save_password', None)
                    else False,
                }
            )

        return make_json_response(
            data={
                'connId': str(trans_id),
                'database': conn.db,
                'serverVersion': conn.manager.version,
            }
        )
    except Exception as e:
        return internal_server_error(errormsg=str(e))


@blueprint.route(
    '/generate/<int:trans_id>/<int:sgid>/<int:sid>/<int:did>',
    methods=["POST"],
    endpoint='generate'
)
@pga_login_required
def generate(trans_id, sgid, sid, did):
    """
    Generate documentation for the specified database.

    Args:
        trans_id: Transaction ID
        sgid: Server group ID
        sid: Server ID
        did: Database ID
    """
    data = {}
    if request.data:
        data = json.loads(request.data)

    format_type = data.get('format', 'markdown')
    include_system_objects = data.get('include_system_objects', False)
    selected_schemas = data.get('selected_schemas', [])

    try:
        manager = get_driver(PG_DEFAULT_DRIVER).connection_manager(sid)
        conn = manager.connection(
            conn_id=trans_id,
            auto_reconnect=True,
            use_binary_placeholder=True,
            did=did
        )

        status, msg = conn.connect()
        if not status:
            return internal_server_error(errormsg=msg)

        engine = DocGenEngine(
            conn=conn,
            include_system_objects=include_system_objects,
            selected_schemas=selected_schemas
        )

        doc_content = engine.generate(format_type)

        return make_json_response(
            data={
                'content': doc_content,
                'format': format_type,
                'database': conn.db,
            }
        )
    except Exception as e:
        return internal_server_error(errormsg=str(e))


@blueprint.route(
    '/download/<int:trans_id>/<int:sgid>/<int:sid>/<int:did>',
    methods=["POST"],
    endpoint='download'
)
@pga_login_required
def download(trans_id, sgid, sid, did):
    """
    Generate and download documentation as a file.

    Args:
        trans_id: Transaction ID
        sgid: Server group ID
        sid: Server ID
        did: Database ID
    """
    data = {}
    if request.data:
        data = json.loads(request.data)

    format_type = data.get('format', 'markdown')
    include_system_objects = data.get('include_system_objects', False)
    selected_schemas = data.get('selected_schemas', [])

    try:
        manager = get_driver(PG_DEFAULT_DRIVER).connection_manager(sid)
        conn = manager.connection(
            conn_id=trans_id,
            auto_reconnect=True,
            use_binary_placeholder=True,
            did=did
        )

        status, msg = conn.connect()
        if not status:
            return internal_server_error(errormsg=msg)

        engine = DocGenEngine(
            conn=conn,
            include_system_objects=include_system_objects,
            selected_schemas=selected_schemas
        )

        doc_content = engine.generate(format_type)

        extension = 'md' if format_type == 'markdown' else 'txt'
        filename = f"{conn.db}_documentation.{extension}"

        return send_file(
            __import__('io', fromlist=['BytesIO']).BytesIO(
                doc_content.encode('utf-8')),
            mimetype='text/markdown' if format_type == 'markdown' else 'text/plain',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return internal_server_error(errormsg=str(e))
