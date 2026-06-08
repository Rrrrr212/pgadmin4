##########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2026, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

import pgadmin.browser.server_groups.servers.roles.tests.utils as roles_utils
import pgadmin.browser.server_groups.servers.tablespaces.tests.utils as \
    tablespace_utils
from pgadmin.browser.server_groups.servers.databases.schemas.tests import\
    utils as schema_utils
from pgadmin.browser.server_groups.servers.databases.schemas.functions.tests\
    import utils as trigger_funcs_utils
from regression.python_test_utils import test_utils
from regression.test_setup import config_data


global node_info_dict
node_info_dict = {
    "sid": [],  # server
    "did": [],  # database
    "lrid": [],  # role
    "tsid": [],  # tablespace
    "scid": [],  # schema
    "oid": []  # directory
}

global parent_node_dict
parent_node_dict = {
    "server": [],
    "database": [],
    "tablespace": [],
    "role": [],
    "schema": [],
    "directory": []
}

_regression_app = None
_regression_test_client = None


def get_regression_test_client():
    global _regression_app
    global _regression_test_client

    if _regression_test_client is None:
        from regression.runtests import app, test_client

        credentials = config_data.get('pgAdmin4_login_credentials', {})
        test_client.test_config_data = {
            'login_username': credentials.get('login_username'),
            'login_password': credentials.get('login_password')
        }
        test_utils.login_using_user_account(test_client)

        _regression_app = app
        _regression_test_client = test_client

    return _regression_app, _regression_test_client
