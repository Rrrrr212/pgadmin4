import os
from flask import request, url_for
from flask_babel import gettext
from pgadmin.user_login_check import pga_login_required
from pgadmin.utils import PgAdminModule
from pgadmin.utils.ajax import make_json_response, bad_request
from pgadmin.utils.driver import get_driver
from config import PG_DEFAULT_DRIVER

from .engine import generate_database_markdown

MODULE_NAME = 'docgen'

class DocGenModule(PgAdminModule):
    LABEL = gettext("Database Document Generator")

    def get_own_javascripts(self):
        return [{
            'name': 'pgadmin.tools.docgen',
            'path': url_for('docgen.static', filename='js/docgen'),
            'when': None
        }]

    def get_own_menuitems(self):
        return {}
        
    def get_exposed_url_endpoints(self):
        return ['docgen.generate']

blueprint = DocGenModule(MODULE_NAME, __name__, static_url_path='/static')

@blueprint.route('/generate/<int:sgid>/<int:sid>/<int:did>', methods=['POST'])
@pga_login_required
def generate(sgid, sid, did):
    """
    Generate markdown documentation for the specified database.
    """
    try:
        manager = get_driver(PG_DEFAULT_DRIVER).connection_manager(sid)
        conn = manager.connection(did=did)
        if not conn.connected():
            status, msg = conn.connect()
            if not status:
                return bad_request(msg)
                
        options = request.json or {}
        
        # Generate markdown using engine
        markdown_content = generate_database_markdown(conn, options)
        
        return make_json_response(
            data={'markdown': markdown_content},
            status=200
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return bad_request(str(e))
