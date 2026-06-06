import re
from datetime import datetime, timezone

from config import PG_DEFAULT_DRIVER
from pgadmin.utils.driver import get_driver
from pgadmin.utils.server_access import get_server


class DatabaseDocGenerator:
    def __init__(self, sid, did):
        self.sid = sid
        self.did = did
        self.manager = get_driver(PG_DEFAULT_DRIVER).connection_manager(sid)
        self.conn = self.manager.connection(did=did, auto_reconnect=True)

        if not self.conn.connected():
            status, error = self.conn.connect()
            if not status:
                raise RuntimeError(error)

    def generate(self, include_tables=True, include_views=True,
                 include_functions=True):
        database_meta = self._get_database_metadata()
        tables = self._get_relations(['r', 'p', 'f']) if include_tables else []
        views = self._get_relations(['v', 'm']) if include_views else []
        functions = self._get_functions() if include_functions else []

        markdown = self._render_markdown(database_meta, tables, views,
                                         functions)

        return {
            'database': database_meta['database_name'],
            'server': database_meta['server_name'],
            'filename': self._build_filename(
                database_meta['server_name'],
                database_meta['database_name']
            ),
            'markdown': markdown,
            'summary': {
                'tables': len(tables),
                'views': len(views),
                'functions': len(functions),
            },
        }

    def _execute(self, sql, params=None):
        if params is None:
            status, result = self.conn.execute_dict(sql)
        else:
            status, result = self.conn.execute_dict(sql, params)

        if not status:
            raise RuntimeError(result)

        return result.get('rows', [])

    def _get_database_metadata(self):
        rows = self._execute(
            """
            SELECT
                current_database() AS database_name,
                current_user AS current_user,
                version() AS server_version
            """
        )
        row = rows[0] if rows else {}
        server = get_server(self.sid)

        return {
            'database_name': row.get('database_name', ''),
            'current_user': row.get('current_user', ''),
            'server_version': row.get('server_version', ''),
            'server_name': getattr(server, 'name', None) or
            'server_{0}'.format(self.sid),
            'generated_at': datetime.now(timezone.utc).isoformat(),
        }

    def _get_relations(self, relkinds):
        placeholders = ', '.join(['%s'] * len(relkinds))
        relation_rows = self._execute(
            """
            SELECT
                ns.nspname AS schema_name,
                cls.relname AS object_name,
                cls.relkind AS relkind,
                obj_description(cls.oid, 'pg_class') AS description
            FROM pg_catalog.pg_class AS cls
            JOIN pg_catalog.pg_namespace AS ns
                ON ns.oid = cls.relnamespace
            WHERE cls.relkind IN ({0})
                AND ns.nspname NOT IN ('pg_catalog', 'information_schema')
                AND ns.nspname NOT LIKE 'pg_toast%'
                AND ns.nspname NOT LIKE 'pg_temp_%'
            ORDER BY ns.nspname, cls.relname
            """.format(placeholders),
            relkinds,
        )

        column_rows = self._execute(
            """
            SELECT
                ns.nspname AS schema_name,
                cls.relname AS object_name,
                cls.relkind AS relkind,
                att.attnum AS ordinal_position,
                att.attname AS column_name,
                pg_catalog.format_type(att.atttypid, att.atttypmod) AS data_type,
                NOT att.attnotnull AS is_nullable,
                pg_catalog.pg_get_expr(def.adbin, def.adrelid) AS default_value,
                pg_catalog.col_description(att.attrelid, att.attnum) AS description
            FROM pg_catalog.pg_attribute AS att
            JOIN pg_catalog.pg_class AS cls
                ON cls.oid = att.attrelid
            JOIN pg_catalog.pg_namespace AS ns
                ON ns.oid = cls.relnamespace
            LEFT JOIN pg_catalog.pg_attrdef AS def
                ON def.adrelid = att.attrelid
                AND def.adnum = att.attnum
            WHERE cls.relkind IN ({0})
                AND att.attnum > 0
                AND NOT att.attisdropped
                AND ns.nspname NOT IN ('pg_catalog', 'information_schema')
                AND ns.nspname NOT LIKE 'pg_toast%'
                AND ns.nspname NOT LIKE 'pg_temp_%'
            ORDER BY ns.nspname, cls.relname, att.attnum
            """.format(placeholders),
            relkinds,
        )

        column_map = {}
        for row in column_rows:
            key = (row['schema_name'], row['object_name'])
            column_map.setdefault(key, []).append({
                'name': row['column_name'],
                'data_type': row['data_type'],
                'nullable': row['is_nullable'],
                'default': row['default_value'],
                'description': row['description'],
            })

        relations = []
        for row in relation_rows:
            key = (row['schema_name'], row['object_name'])
            relations.append({
                'schema_name': row['schema_name'],
                'object_name': row['object_name'],
                'object_type': self._relation_type_label(row['relkind']),
                'description': row['description'],
                'columns': column_map.get(key, []),
            })

        return relations

    def _get_functions(self):
        rows = self._execute(
            """
            SELECT
                ns.nspname AS schema_name,
                proc.proname AS object_name,
                proc.prokind AS prokind,
                pg_catalog.pg_get_function_identity_arguments(proc.oid) AS arguments,
                pg_catalog.pg_get_function_result(proc.oid) AS return_type,
                lang.lanname AS language,
                obj_description(proc.oid, 'pg_proc') AS description
            FROM pg_catalog.pg_proc AS proc
            JOIN pg_catalog.pg_namespace AS ns
                ON ns.oid = proc.pronamespace
            JOIN pg_catalog.pg_language AS lang
                ON lang.oid = proc.prolang
            WHERE proc.prokind IN ('f', 'p')
                AND ns.nspname NOT IN ('pg_catalog', 'information_schema')
                AND ns.nspname NOT LIKE 'pg_toast%'
                AND ns.nspname NOT LIKE 'pg_temp_%'
            ORDER BY ns.nspname, proc.proname,
                pg_catalog.pg_get_function_identity_arguments(proc.oid)
            """
        )

        return [{
            'schema_name': row['schema_name'],
            'object_name': row['object_name'],
            'object_type': 'Procedure' if row['prokind'] == 'p' else 'Function',
            'arguments': row['arguments'] or '',
            'return_type': row['return_type'],
            'language': row['language'],
            'description': row['description'],
        } for row in rows]

    def _render_markdown(self, database_meta, tables, views, functions):
        lines = [
            '# Database Documentation for `{0}`'.format(
                database_meta['database_name']
            ),
            '',
            '## Overview',
            '',
            '- Server: `{0}`'.format(database_meta['server_name']),
            '- Database: `{0}`'.format(database_meta['database_name']),
            '- User: `{0}`'.format(database_meta['current_user']),
            '- Generated at: `{0}`'.format(database_meta['generated_at']),
            '- Tables: {0}'.format(len(tables)),
            '- Views: {0}'.format(len(views)),
            '- Functions: {0}'.format(len(functions)),
            '',
        ]

        lines.extend(self._render_relation_section('Tables', tables))
        lines.extend(self._render_relation_section('Views', views))
        lines.extend(self._render_function_section(functions))

        return '\n'.join(lines).strip() + '\n'

    def _render_relation_section(self, title, relations):
        lines = ['## {0}'.format(title), '']

        if not relations:
            lines.extend(['_No objects found._', ''])
            return lines

        for relation in relations:
            full_name = '{0}.{1}'.format(
                relation['schema_name'], relation['object_name']
            )
            lines.extend([
                '### `{0}`'.format(full_name),
                '',
                '- Type: {0}'.format(relation['object_type']),
                '- Comment: {0}'.format(
                    self._inline_text(relation['description'])
                ),
                '',
            ])

            if relation['columns']:
                lines.extend([
                    '| Column | Type | Nullable | Default | Comment |',
                    '| --- | --- | --- | --- | --- |',
                ])
                for column in relation['columns']:
                    lines.append(
                        '| {0} | {1} | {2} | {3} | {4} |'.format(
                            self._table_cell(column['name']),
                            self._table_cell(column['data_type']),
                            'Yes' if column['nullable'] else 'No',
                            self._table_cell(column['default']),
                            self._table_cell(column['description']),
                        )
                    )
            else:
                lines.append('_No columns found._')

            lines.append('')

        return lines

    def _render_function_section(self, functions):
        lines = ['## Functions', '']

        if not functions:
            lines.extend(['_No objects found._', ''])
            return lines

        for function in functions:
            signature = '{0}.{1}({2})'.format(
                function['schema_name'],
                function['object_name'],
                function['arguments'],
            )
            lines.extend([
                '### `{0}`'.format(signature),
                '',
                '- Type: {0}'.format(function['object_type']),
                '- Returns: `{0}`'.format(function['return_type']),
                '- Language: `{0}`'.format(function['language']),
                '- Comment: {0}'.format(
                    self._inline_text(function['description'])
                ),
                '',
            ])

        return lines

    def _relation_type_label(self, relkind):
        mapping = {
            'r': 'Table',
            'p': 'Partitioned Table',
            'f': 'Foreign Table',
            'v': 'View',
            'm': 'Materialized View',
        }
        return mapping.get(relkind, 'Relation')

    def _inline_text(self, value):
        if value is None or str(value).strip() == '':
            return '_No comment available._'
        return str(value).replace('\r\n', ' ').replace('\n', ' ')

    def _table_cell(self, value):
        if value is None or str(value).strip() == '':
            return '—'
        return str(value).replace('|', '\\|').replace('\r\n', '<br>').replace(
            '\n', '<br>'
        )

    def _build_filename(self, server_name, database_name):
        raw_name = '{0}_{1}_database_documentation.md'.format(
            server_name,
            database_name,
        )
        return re.sub(r'[^A-Za-z0-9._-]+', '_', raw_name)
