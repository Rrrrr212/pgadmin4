##########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2026, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

import os
import time
import secrets
import json
import pytest

from pgadmin.utils.route import BaseTestGenerator
from regression import parent_node_dict
from regression.python_test_utils import test_utils as utils
from pgadmin.utils import does_utility_exist, server_utils
import pgadmin.tools.backup.tests.test_backup_utils as backup_utils


class BackupRestoreTestGenerator(BaseTestGenerator):
    """Backup and Restore automated test suite for PostgreSQL and EPAS"""

    scenarios = [
        ('PostgreSQL database full backup and restore (< v16)',
         dict(
             db_type='postgres',
             backup_params=dict(
                 file='test_backup_pg',
                 format='custom',
                 verbose=True,
                 blobs=True,
                 schemas=[],
                 tables=[],
                 database='test_backup_restore_pg',
             ),
             backup_url='/backup/job/{0}/object',
             backup_expected_params=dict(
                 expected_cmd_opts=['--verbose', '--format=c', '--blobs'],
                 not_expected_cmd_opts=[],
                 expected_exit_code=[0, None]
             ),
             restore_params=dict(
                 file='test_backup_pg',
                 format='custom',
                 verbose=True,
                 schemas=[],
                 tables=[],
                 database='test_restore_pg'
             ),
             restore_url='/restore/job/{0}',
             restore_expected_cmd_opts=['--verbose'],
             restore_not_expected_cmd_opts=[],
             restore_expected_exit_code=[0, None],
             server_max_version=159999,
             message='--blobs is deprecated and not supported by servers greater than 15'
         )),
        ('PostgreSQL database full backup and restore (>= v16)',
         dict(
             db_type='postgres',
             backup_params=dict(
                 file='test_backup_pg',
                 format='custom',
                 verbose=True,
                 blobs=True,
                 schemas=[],
                 tables=[],
                 database='test_backup_restore_pg',
             ),
             backup_url='/backup/job/{0}/object',
             backup_expected_params=dict(
                 expected_cmd_opts=['--verbose', '--format=c', '--large-objects'],
                 not_expected_cmd_opts=[],
                 expected_exit_code=[0, None]
             ),
             restore_params=dict(
                 file='test_backup_pg',
                 format='custom',
                 verbose=True,
                 schemas=[],
                 tables=[],
                 database='test_restore_pg'
             ),
             restore_url='/restore/job/{0}',
             restore_expected_cmd_opts=['--verbose'],
             restore_not_expected_cmd_opts=[],
             restore_expected_exit_code=[0, None],
             server_min_version=160000,
             message='--large-objects is not supported by servers less than 16'
         )),
        ('EPAS database full backup and restore (< v16)',
         dict(
             db_type='ppas',
             backup_params=dict(
                 file='test_backup_epas',
                 format='custom',
                 verbose=True,
                 blobs=True,
                 schemas=[],
                 tables=[],
                 database='test_backup_restore_epas',
             ),
             backup_url='/backup/job/{0}/object',
             backup_expected_params=dict(
                 expected_cmd_opts=['--verbose', '--format=c', '--blobs'],
                 not_expected_cmd_opts=[],
                 expected_exit_code=[0, None]
             ),
             restore_params=dict(
                 file='test_backup_epas',
                 format='custom',
                 verbose=True,
                 schemas=[],
                 tables=[],
                 database='test_restore_epas'
             ),
             restore_url='/restore/job/{0}',
             restore_expected_cmd_opts=['--verbose'],
             restore_not_expected_cmd_opts=[],
             restore_expected_exit_code=[0, None],
             server_max_version=159999,
             message='--blobs is deprecated and not supported by servers greater than 15'
         )),
        ('EPAS database full backup and restore (>= v16)',
         dict(
             db_type='ppas',
             backup_params=dict(
                 file='test_backup_epas',
                 format='custom',
                 verbose=True,
                 blobs=True,
                 schemas=[],
                 tables=[],
                 database='test_backup_restore_epas',
             ),
             backup_url='/backup/job/{0}/object',
             backup_expected_params=dict(
                 expected_cmd_opts=['--verbose', '--format=c', '--large-objects'],
                 not_expected_cmd_opts=[],
                 expected_exit_code=[0, None]
             ),
             restore_params=dict(
                 file='test_backup_epas',
                 format='custom',
                 verbose=True,
                 schemas=[],
                 tables=[],
                 database='test_restore_epas'
             ),
             restore_url='/restore/job/{0}',
             restore_expected_cmd_opts=['--verbose'],
             restore_not_expected_cmd_opts=[],
             restore_expected_exit_code=[0, None],
             server_min_version=160000,
             message='--large-objects is not supported by servers less than 16'
         ))
    ]

    def setUp(self):
        if hasattr(self, 'server_min_version') and \
            self.server_information['server_version'] < \
                self.server_min_version:
            self.skipTest(self.message)

        if hasattr(self, 'server_max_version') and \
            self.server_information['server_version'] > \
                self.server_max_version:
            self.skipTest(self.message)

        if 'default_binary_paths' not in self.server or \
            self.server['default_binary_paths'] is None or \
            self.db_type not in self.server['default_binary_paths'] or \
                self.server['default_binary_paths'][self.db_type] == '':
            self.skipTest(
                "default_binary_paths for {0} is not set for server {1}".format(
                    self.db_type, self.server['name']
                )
            )

        binary_path_pgdump = os.path.join(
            self.server['default_binary_paths'][self.db_type],
            'pg_dump')
        binary_path_pgrestore = os.path.join(
            self.server['default_binary_paths'][self.db_type],
            'pg_restore')

        if os.name == 'nt':
            binary_path_pgdump = binary_path_pgdump + '.exe'
            binary_path_pgrestore = binary_path_pgrestore + '.exe'

        ret_val = does_utility_exist(binary_path_pgdump)
        if ret_val is not None:
            self.skipTest(ret_val)

        ret_val = does_utility_exist(binary_path_pgrestore)
        if ret_val is not None:
            self.skipTest(ret_val)

        server_con = server_utils.connect_server(self, self.server_id)
        if 'data' in server_con and 'type' in server_con['data']:
            server_type = server_con['data']['type']
            if server_type != self.db_type:
                self.skipTest(
                    "Test skipped: server type is {0}, expected {1}".format(
                        server_type, self.db_type)
                )

    def runTest(self):
        self.server_id = parent_node_dict["server"][-1]["server_id"]
        server_utils.connect_server(self, self.server_id)

        source_db = self.backup_params['database']
        target_db = self.restore_params['database']

        utils.create_database(self.server, source_db)

        connection = utils.get_db_connection(
            source_db,
            self.server['username'],
            self.server['db_password'],
            self.server['host'],
            self.server['port'],
            self.server['sslmode']
        )
        cursor = connection.cursor()
        cursor.execute('''CREATE TABLE test_table (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            value INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        for i in range(10):
            cursor.execute(
                '''INSERT INTO test_table (name, value) VALUES (%s, %s)''',
                (f'test_{i}', i * 100)
            )
        connection.commit()
        connection.close()

        backup_url = self.backup_url.format(self.server_id)
        job_id = backup_utils.create_backup_job(
            self.tester, backup_url, self.backup_params, self.assertEqual)
        backup_file = backup_utils.run_backup_job(
            self.tester,
            job_id,
            self.backup_expected_params,
            self.assertIn,
            self.assertNotIn,
            self.assertEqual
        )

        utils.create_database(self.server, target_db)

        restore_url = self.restore_url.format(self.server_id)
        response = self.tester.post(restore_url,
                                   data=json.dumps(self.restore_params),
                                   content_type='html/json')
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data.decode('utf-8'))
        job_id = response_data['data']['job_id']

        the_process = None
        for _ in range(60):
            response1 = self.tester.get('/misc/bgprocess/?_={0}'.format(
                secrets.choice(range(1, 9999999)))
            )
            self.assertEqual(response1.status_code, 200)
            process_list = json.loads(response1.data.decode('utf-8'))

            try:
                the_process = next(
                    p for p in process_list if p['id'] == job_id)
            except StopIteration:
                the_process = None

            if the_process and the_process.get('exit_code') is not None:
                break
            time.sleep(0.5)

        self.assertTrue('execution_time' in the_process)
        self.assertTrue('stime' in the_process)
        self.assertTrue('exit_code' in the_process)
        self.assertTrue(
            the_process['exit_code'] in self.restore_expected_exit_code)

        if self.restore_expected_cmd_opts:
            for opt in self.restore_expected_cmd_opts:
                self.assertIn(opt, the_process['details']['cmd'])
        if self.restore_not_expected_cmd_opts:
            for opt in self.restore_not_expected_cmd_opts:
                self.assertNotIn(opt, the_process['details']['cmd'])

        restore_ack = self.tester.put('/misc/bgprocess/{0}'.format(job_id))
        self.assertEqual(restore_ack.status_code, 200)
        restore_ack_res = json.loads(restore_ack.data.decode('utf-8'))
        self.assertEqual(restore_ack_res['success'], 1)

        if backup_file is not None and os.path.isfile(backup_file):
            os.remove(backup_file)

        connection = utils.get_db_connection(
            target_db,
            self.server['username'],
            self.server['db_password'],
            self.server['host'],
            self.server['port'],
            self.server['sslmode']
        )
        cursor = connection.cursor()
        cursor.execute('SELECT COUNT(*) FROM test_table')
        count = cursor.fetchone()[0]
        self.assertEqual(count, 10, "Expected 10 rows after restore")

        cursor.execute('SELECT * FROM test_table ORDER BY id')
        rows = cursor.fetchall()
        for i, row in enumerate(rows):
            self.assertEqual(row[1], f'test_{i}')
            self.assertEqual(row[2], i * 100)

        connection.close()

    def tearDown(self):
        try:
            connection = utils.get_db_connection(
                self.server['db'],
                self.server['username'],
                self.server['db_password'],
                self.server['host'],
                self.server['port'],
                self.server['sslmode']
            )
            if hasattr(self, 'backup_params'):
                utils.drop_database(connection, self.backup_params['database'])
            if hasattr(self, 'restore_params'):
                utils.drop_database(connection, self.restore_params['database'])
        except Exception:
            pass
