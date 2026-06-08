##########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2026, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

import json
import os
import tempfile
import pytest
from regression.python_test_utils import test_utils
from regression import node_info_dict


class TestBackupRestore:
    """Test class for backup/restore functionality"""

    @pytest.fixture(autouse=True)
    def setup(self, app_client):
        self.client = app_client
        self.server_data = test_utils.get_config_data()
        self.test_database = "test_backup_restore_db"
        self.test_table = "test_backup_table"
        self.backup_file = None

        yield

        self._cleanup()

    def _get_server_by_type(self, db_type="pg"):
        for server in self.server_data:
            if server.get('db_type', 'pg') == db_type:
                return server
        return self.server_data[0] if self.server_data else None

    def _create_test_database(self, server):
        connection = test_utils.get_db_connection(
            server['db'],
            server['username'],
            server['db_password'],
            server['host'],
            server['port'],
            server['sslmode']
        )
        test_utils.drop_database(connection, self.test_database)
        db_id = test_utils.create_database(server, self.test_database)
        connection.close()
        return db_id

    def _create_test_data(self, server):
        test_utils.create_table(
            server,
            self.test_database,
            self.test_table
        )

    def _cleanup(self):
        for server in self.server_data:
            try:
                connection = test_utils.get_db_connection(
                    server['db'],
                    server['username'],
                    server['db_password'],
                    server['host'],
                    server['port'],
                    server['sslmode']
                )
                test_utils.drop_database(connection, self.test_database)
                connection.close()
            except Exception:
                pass

        if self.backup_file and os.path.exists(self.backup_file):
            try:
                os.remove(self.backup_file)
            except Exception:
                pass

    def _add_server(self, server):
        response = self.client.post(
            '/browser/server_groups/1/servers',
            data=json.dumps({
                "name": server['name'],
                "comment": server['comment'],
                "host": server['host'],
                "port": server['port'],
                "username": server['username'],
                "password": server['db_password'],
                "sslmode": server['sslmode'],
                "maintenance_db": server['db'],
                "db_res": ["postgres", self.test_database],
                "role": "",
                "passfile": "",
                "bgcolor": "#ffffff",
                "fgcolor": "#000000",
                "shared": False,
                "group": 1
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        return json.loads(response.data)

    def _get_database_id(self, server):
        response = self.client.get(
            '/browser/servers/1/databases',
            follow_redirects=True
        )
        assert response.status_code == 200
        databases = json.loads(response.data)
        for db in databases:
            if db.get('name') == self.test_database:
                return db['id']
        return None

    def _create_backup(self, server, db_id, format='custom'):
        self.backup_file = tempfile.mktemp(suffix='.backup')

        response = self.client.post(
            f'/browser/server_groups/1/servers/1/databases/{db_id}/backup',
            data=json.dumps({
                "file": self.backup_file,
                "format": format,
                "database": self.test_database,
                "blobs": True,
                "use_insert_commands": False,
                "verbose": True
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        return json.loads(response.data)

    def _restore_backup(self, server, db_id):
        response = self.client.post(
            f'/browser/server_groups/1/servers/1/databases/{db_id}/restore',
            data=json.dumps({
                "file": self.backup_file,
                "database": self.test_database,
                "verbose": True
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        return json.loads(response.data)

    def _verify_data_exists(self, server):
        connection = test_utils.get_db_connection(
            self.test_database,
            server['username'],
            server['db_password'],
            server['host'],
            server['port'],
            server['sslmode']
        )
        cursor = connection.cursor()
        cursor.execute(
            f"SELECT EXISTS(SELECT 1 FROM information_schema.tables "
            f"WHERE table_name = '{self.test_table}')"
        )
        result = cursor.fetchone()
        connection.close()
        return result[0]

    def _drop_table(self, server):
        test_utils.delete_table(
            server,
            self.test_database,
            self.test_table
        )

    def test_backup_postgresql(self):
        server = self._get_server_by_type('pg')
        if not server:
            pytest.skip("PostgreSQL server not configured")

        if server.get('default_binary_paths', {}).get('pg') is None:
            pytest.skip("default_binary_paths not configured for PostgreSQL")

        self._create_test_database(server)
        self._create_test_data(server)

        server_info = self._add_server(server)
        assert server_info is not None

        db_id = self._get_database_id(server)
        assert db_id is not None

        backup_result = self._create_backup(server, db_id)
        assert backup_result is not None
        assert os.path.exists(self.backup_file)
        assert os.path.getsize(self.backup_file) > 0

    def test_backup_and_restore_postgresql(self):
        server = self._get_server_by_type('pg')
        if not server:
            pytest.skip("PostgreSQL server not configured")

        if server.get('default_binary_paths', {}).get('pg') is None:
            pytest.skip("default_binary_paths not configured for PostgreSQL")

        self._create_test_database(server)
        self._create_test_data(server)

        server_info = self._add_server(server)
        assert server_info is not None

        db_id = self._get_database_id(server)
        assert db_id is not None

        backup_result = self._create_backup(server, db_id)
        assert backup_result is not None
        assert os.path.exists(self.backup_file)

        self._drop_table(server)
        data_exists = self._verify_data_exists(server)
        assert not data_exists

        restore_result = self._restore_backup(server, db_id)
        assert restore_result is not None

    def test_backup_epas(self):
        server = self._get_server_by_type('ppas')
        if not server:
            pytest.skip("EPAS server not configured")

        if server.get('default_binary_paths', {}).get('ppas') is None:
            pytest.skip("default_binary_paths not configured for EPAS")

        self._create_test_database(server)
        self._create_test_data(server)

        server_info = self._add_server(server)
        assert server_info is not None

        db_id = self._get_database_id(server)
        assert db_id is not None

        backup_result = self._create_backup(server, db_id)
        assert backup_result is not None
        assert os.path.exists(self.backup_file)
        assert os.path.getsize(self.backup_file) > 0

    def test_backup_and_restore_epas(self):
        server = self._get_server_by_type('ppas')
        if not server:
            pytest.skip("EPAS server not configured")

        if server.get('default_binary_paths', {}).get('ppas') is None:
            pytest.skip("default_binary_paths not configured for EPAS")

        self._create_test_database(server)
        self._create_test_data(server)

        server_info = self._add_server(server)
        assert server_info is not None

        db_id = self._get_database_id(server)
        assert db_id is not None

        backup_result = self._create_backup(server, db_id)
        assert backup_result is not None
        assert os.path.exists(self.backup_file)

        self._drop_table(server)
        data_exists = self._verify_data_exists(server)
        assert not data_exists

        restore_result = self._restore_backup(server, db_id)
        assert restore_result is not None

    def test_backup_plain_format_postgresql(self):
        server = self._get_server_by_type('pg')
        if not server:
            pytest.skip("PostgreSQL server not configured")

        if server.get('default_binary_paths', {}).get('pg') is None:
            pytest.skip("default_binary_paths not configured for PostgreSQL")

        self._create_test_database(server)
        self._create_test_data(server)

        server_info = self._add_server(server)
        assert server_info is not None

        db_id = self._get_database_id(server)
        assert db_id is not None

        backup_result = self._create_backup(server, db_id, format='plain')
        assert backup_result is not None
        assert os.path.exists(self.backup_file)

        with open(self.backup_file, 'r') as f:
            content = f.read()
            assert 'CREATE TABLE' in content or 'INSERT' in content

    def test_backup_with_schema_only_postgresql(self):
        server = self._get_server_by_type('pg')
        if not server:
            pytest.skip("PostgreSQL server not configured")

        if server.get('default_binary_paths', {}).get('pg') is None:
            pytest.skip("default_binary_paths not configured for PostgreSQL")

        self._create_test_database(server)
        self._create_test_data(server)

        server_info = self._add_server(server)
        assert server_info is not None

        db_id = self._get_database_id(server)
        assert db_id is not None

        response = self.client.post(
            f'/browser/server_groups/1/servers/1/databases/{db_id}/backup',
            data=json.dumps({
                "file": self.backup_file,
                "format": "plain",
                "database": self.test_database,
                "schema_only": True,
                "verbose": True
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        assert os.path.exists(self.backup_file)

        with open(self.backup_file, 'r') as f:
            content = f.read()
            assert 'CREATE TABLE' in content
            assert 'INSERT' not in content
