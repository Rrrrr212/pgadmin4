##########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2026, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from regression import get_regression_test_client


class FakeConnection:
    def connected(self):
        return True


class FakeManager:
    def __init__(self, server_type, version, utility_root, username):
        self.server_type = server_type
        self.version = version
        self.use_ssh_tunnel = False
        self.user = username
        self._utility_root = utility_root
        self._connection = FakeConnection()

    def connection(self):
        return self._connection

    def utility(self, utility_name):
        utilities = {
            'backup': 'pg_dump',
            'backup_server': 'pg_dumpall',
            'restore': 'pg_restore',
            'sql': 'psql'
        }
        return f'{self._utility_root}/{utilities[utility_name]}'


class FakeDriver:
    def __init__(self, manager):
        self._manager = manager

    def connection_manager(self, _sid):
        return self._manager

    def qtIdent(self, _conn, *identifiers):
        return '.'.join(f'"{identifier}"' for identifier in identifiers)


class FakeBatchProcess:
    created_processes = []
    next_process_id = 9000

    def __init__(self, desc, cmd, args, manager_obj):
        self.desc = desc
        self.cmd = cmd
        self.args = args
        self.manager_obj = manager_obj
        self.id = FakeBatchProcess.next_process_id
        self.server = None
        self.started = False

        FakeBatchProcess.next_process_id += 1
        FakeBatchProcess.created_processes.append(self)

    def set_env_variables(self, server):
        self.server = server

    def start(self):
        self.started = True


@pytest.fixture(scope='module')
def regression_client():
    _, client = get_regression_test_client()
    return client


@pytest.fixture(autouse=True)
def reset_fake_processes():
    FakeBatchProcess.created_processes.clear()
    FakeBatchProcess.next_process_id = 9000


@pytest.mark.parametrize(
    'server_type,server_name,utility_root,username,port',
    [
        ('pg', 'PostgreSQL 16', '/opt/postgresql/16/bin', 'postgres', 5432),
        ('ppas', 'EPAS 16', '/opt/edb/as16/bin', 'enterprisedb', 5444),
    ],
    ids=['postgresql', 'epas']
)
def test_backup_job_flow_simulates_database_types(
    regression_client,
    server_type,
    server_name,
    utility_root,
    username,
    port
):
    server = SimpleNamespace(
        id=1,
        host='127.0.0.1',
        port=port,
        username=username,
        maintenance_db='postgres',
        name=server_name,
        service=None
    )
    manager = FakeManager(server_type, 160000, utility_root, username)
    driver = FakeDriver(manager)
    backup_path = f'/tmp/{server_type}_backup.dump'
    payload = {
        'file': f'{server_type}_backup.dump',
        'format': 'custom',
        'verbose': True,
        'blobs': True,
        'schemas': [],
        'tables': [],
        'database': 'postgres'
    }

    with patch('pgadmin.tools.backup.get_server', return_value=server), \
         patch('pgadmin.tools.backup.does_utility_exist', return_value=None), \
         patch('pgadmin.tools.backup.filename_with_file_manager_path',
               return_value=backup_path), \
         patch('pgadmin.tools.backup.BatchProcess', FakeBatchProcess), \
         patch('pgadmin.utils.driver.get_driver', return_value=driver):
        response = regression_client.post(
            '/backup/job/1/object',
            data=json.dumps(payload),
            content_type='application/json'
        )

    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['data']['job_id'] == 9000

    process = FakeBatchProcess.created_processes[-1]
    process_details = process.desc.details(process.cmd, process.args)

    assert process.started is True
    assert process.server is server
    assert process.cmd == f'{utility_root}/pg_dump'
    assert '--host' in process.args
    assert '127.0.0.1' in process.args
    assert '--port' in process.args
    assert str(port) in process.args
    assert '--username' in process.args
    assert username in process.args
    assert '--verbose' in process.args
    assert '--format=c' in process.args
    assert '--large-objects' in process.args
    assert process.args[-1] == 'postgres'
    assert process_details['type'] == 'Backup Object'
    assert server_name in process_details['message']
    assert f'{utility_root}/pg_dump' in process_details['cmd']


@pytest.mark.parametrize(
    'server_type,server_name,utility_root,username,port',
    [
        ('pg', 'PostgreSQL 16', '/opt/postgresql/16/bin', 'postgres', 5432),
        ('ppas', 'EPAS 16', '/opt/edb/as16/bin', 'enterprisedb', 5444),
    ],
    ids=['postgresql', 'epas']
)
def test_restore_job_flow_simulates_database_types(
    regression_client,
    server_type,
    server_name,
    utility_root,
    username,
    port
):
    server = SimpleNamespace(
        id=1,
        host='127.0.0.1',
        port=port,
        username=username,
        maintenance_db='postgres',
        name=server_name,
        service=None
    )
    manager = FakeManager(server_type, 160000, utility_root, username)
    driver = FakeDriver(manager)
    restore_path = f'/tmp/{server_type}_restore.dump'
    payload = {
        'file': f'{server_type}_restore.dump',
        'format': 'custom',
        'custom': False,
        'verbose': True,
        'schemas': [],
        'tables': [],
        'database': 'postgres'
    }

    with patch('pgadmin.tools.restore.get_server', return_value=server), \
         patch('pgadmin.tools.restore.does_utility_exist', return_value=None), \
         patch('pgadmin.tools.restore.filename_with_file_manager_path',
               return_value=restore_path), \
         patch('pgadmin.tools.restore.BatchProcess', FakeBatchProcess), \
         patch('pgadmin.utils.driver.get_driver', return_value=driver):
        response = regression_client.post(
            '/restore/job/1',
            data=json.dumps(payload),
            content_type='application/json'
        )

    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['data']['job_id'] == 9000

    process = FakeBatchProcess.created_processes[-1]
    process_details = process.desc.details(process.cmd, process.args)

    assert process.started is True
    assert process.server is server
    assert process.cmd == f'{utility_root}/pg_restore'
    assert '--host' in process.args
    assert '127.0.0.1' in process.args
    assert '--port' in process.args
    assert str(port) in process.args
    assert '--username' in process.args
    assert username in process.args
    assert '--dbname' in process.args
    assert '--verbose' in process.args
    assert process.args[-1] == restore_path
    assert process_details['type'] == 'Restore'
    assert server_name in process_details['message']
    assert f'{utility_root}/pg_restore' in process_details['cmd']
