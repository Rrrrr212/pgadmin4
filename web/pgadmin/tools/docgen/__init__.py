from flask import current_app, request
from flask_babel import gettext
from pgadmin.user_login_check import pga_login_required
from pgadmin.utils import PgAdminModule
from pgadmin.utils.ajax import bad_request, internal_server_error, \
    make_json_response

from .engine import DatabaseDocGenerator

MODULE_NAME = 'docgen'


class DocGenModule(PgAdminModule):
    LABEL = gettext('Database document generator')

    def get_exposed_url_endpoints(self):
        return ['docgen.generate']


blueprint = DocGenModule(MODULE_NAME, __name__, static_url_path='')


def _to_bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ['1', 'true', 't', 'yes', 'y', 'on']


@blueprint.route('/', endpoint='index')
@pga_login_required
def index():
    return bad_request(errormsg=gettext('This URL cannot be called directly.'))


@blueprint.route('/generate', methods=['POST'], endpoint='generate')
@pga_login_required
def generate():
    payload = request.get_json(silent=True) or request.form or {}

    sid = payload.get('sid')
    did = payload.get('did')
    output_format = payload.get('format', 'markdown')

    if sid is None or did is None:
        return bad_request(errormsg=gettext(
            'Both server id and database id are required.'
        ))

    if output_format != 'markdown':
        return bad_request(errormsg=gettext(
            'Only Markdown output is currently supported.'
        ))

    try:
        generator = DatabaseDocGenerator(int(sid), int(did))
        result = generator.generate(
            include_tables=_to_bool(payload.get('include_tables'), True),
            include_views=_to_bool(payload.get('include_views'), True),
            include_functions=_to_bool(
                payload.get('include_functions'), True
            ),
        )
        return make_json_response(data=result)
    except ValueError as error:
        return bad_request(errormsg=str(error))
    except Exception as error:
        current_app.logger.exception(error)
        return internal_server_error(errormsg=gettext(
            'Failed to generate database documentation.'
        ))
