##########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2026, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

"""Database documentation generation engine."""
import textwrap


class DocGenEngine:
    """Engine for generating database documentation."""

    def __init__(self, conn):
        self.conn = conn

    def generate(self, output_format, include_tables, include_views,
                 include_functions, schema_filter):
        if output_format != 'markdown':
            output_format = 'markdown'

        sections = []

        sections.append(self._build_header())

        if include_tables:
            sections.append(self._build_tables_section(schema_filter))

        if include_views:
            sections.append(self._build_views_section(schema_filter))

        if include_functions:
            sections.append(self._build_functions_section(schema_filter))

        return '\n\n'.join(sections)

    def _build_header(self):
        db_name = self.conn.db
        version = self.conn.manager.version
        return textwrap.dedent(f"""\
        # Database Documentation

        **Database**: {db_name}
        **Server Version**: {version}
        """)

    def _build_tables_section(self, schema_filter):
        tables = self._fetch_tables(schema_filter)
        if not tables:
            return '## Tables\n\n*No tables found.*'

        lines = ['## Tables', '', '| # | Name | Schema | Comment | Columns |']
        lines.append('|---|------|--------|---------|---------|')

        for idx, table in enumerate(tables, 1):
            comment = table.get('description', '') or ''
            lines.append(
                f'| {idx} | {table["name"]} | {table["schema"]} '
                f'| {comment} | {table.get("column_count", 0)} |'
            )

        lines.append('')

        for table in tables:
            lines.extend(self._build_table_detail(table))

        return '\n'.join(lines)

    def _build_table_detail(self, table):
        lines = [
            f'### {table["schema"]}.{table["name"]}',
            '',
        ]

        if table.get('description'):
            lines.append(f'> {table["description"]}')
            lines.append('')

        columns = self._fetch_columns(
            table['schema'], table['name'], 'TABLE'
        )

        if columns:
            lines.append('| # | Column | Type | Nullable | Default | Comment |')
            lines.append('|---|--------|------|----------|---------|---------|')
            for idx, col in enumerate(columns, 1):
                nullable = 'YES' if col.get('is_nullable') == 'YES' else 'NO'
                default = col.get('column_default', '') or ''
                comment = col.get('description', '') or ''
                lines.append(
                    f'| {idx} | {col["name"]} | {col["udt_name"]} '
                    f'| {nullable} | {default} | {comment} |'
                )
            lines.append('')

        indexes = self._fetch_indexes(table['schema'], table['name'])
        if indexes:
            lines.append('**Indexes:**')
            lines.append('')
            lines.append('| # | Name | Columns | Unique |')
            lines.append('|---|------|---------|--------|')
            for idx, idx_info in enumerate(indexes, 1):
                unique = 'YES' if idx_info.get('is_unique') else 'NO'
                lines.append(
                    f'| {idx} | {idx_info["name"]} '
                    f'| {idx_info.get("columns", "")} '
                    f'| {unique} |'
                )
            lines.append('')

        constraints = self._fetch_constraints(table['schema'], table['name'])
        if constraints:
            lines.append('**Constraints:**')
            lines.append('')
            lines.append('| # | Name | Type | Definition |')
            lines.append('|---|------|------|------------|')
            for idx, con in enumerate(constraints, 1):
                lines.append(
                    f'| {idx} | {con["name"]} '
                    f'| {con.get("constraint_type", "")} '
                    f'| {con.get("definition", "")} |'
                )
            lines.append('')

        triggers = self._fetch_triggers(table['schema'], table['name'])
        if triggers:
            lines.append('**Triggers:**')
            lines.append('')
            lines.append('| # | Name | Timing | Event |')
            lines.append('|---|------|--------|-------|')
            for idx, trig in enumerate(triggers, 1):
                lines.append(
                    f'| {idx} | {trig["name"]} '
                    f'| {trig.get("timing", "")} '
                    f'| {trig.get("event", "")} |'
                )
            lines.append('')

        return lines

    def _build_views_section(self, schema_filter):
        views = self._fetch_views(schema_filter)
        if not views:
            return '## Views\n\n*No views found.*'

        lines = ['## Views', '', '| # | Name | Schema | Comment |']
        lines.append('|---|------|--------|---------|')

        for idx, view in enumerate(views, 1):
            comment = view.get('description', '') or ''
            lines.append(
                f'| {idx} | {view["name"]} | {view["schema"]} '
                f'| {comment} |'
            )

        lines.append('')

        for view in views:
            lines.extend(self._build_view_detail(view))

        return '\n'.join(lines)

    def _build_view_detail(self, view):
        lines = [
            f'### {view["schema"]}.{view["name"]}',
            '',
        ]

        if view.get('description'):
            lines.append(f'> {view["description"]}')
            lines.append('')

        definition = view.get('definition', '')
        if definition:
            lines.append('```sql')
            lines.append(definition.strip())
            lines.append('```')
            lines.append('')

        columns = self._fetch_columns(
            view['schema'], view['name'], 'VIEW'
        )
        if columns:
            lines.append('| # | Column | Type | Comment |')
            lines.append('|---|--------|------|---------|')
            for idx, col in enumerate(columns, 1):
                comment = col.get('description', '') or ''
                lines.append(
                    f'| {idx} | {col["name"]} | {col["udt_name"]} '
                    f'| {comment} |'
                )
            lines.append('')

        return lines

    def _build_functions_section(self, schema_filter):
        functions = self._fetch_functions(schema_filter)
        if not functions:
            return '## Functions\n\n*No functions found.*'

        lines = ['## Functions', '', '| # | Name | Schema | Returns | Comment |']
        lines.append('|---|------|--------|---------|---------|')

        for idx, func in enumerate(functions, 1):
            comment = func.get('description', '') or ''
            returns = func.get('return_type', '') or ''
            lines.append(
                f'| {idx} | {func["name"]} | {func["schema"]} '
                f'| {returns} | {comment} |'
            )

        lines.append('')

        for func in functions:
            lines.extend(self._build_function_detail(func))

        return '\n'.join(lines)

    def _build_function_detail(self, func):
        lines = [
            f'### {func["schema"]}.{func["name"]}',
            '',
        ]

        if func.get('description'):
            lines.append(f'> {func["description"]}')
            lines.append('')

        signature = func.get('signature', '')
        if signature:
            lines.append('```sql')
            lines.append(signature.strip())
            lines.append('```')
            lines.append('')

        definition = func.get('definition', '')
        if definition:
            lines.append('**Source Code:**')
            lines.append('')
            lines.append('```sql')
            lines.append(definition.strip())
            lines.append('```')
            lines.append('')

        return lines

    def _fetch_tables(self, schema_filter):
        sql = """
        SELECT
            t.oid,
            t.relname AS name,
            n.nspname AS schema,
            obj_description(t.oid, 'pg_class') AS description,
            (SELECT count(*) FROM pg_attribute a
             WHERE a.attrelid = t.oid
               AND a.attnum > 0
               AND NOT a.attisdropped) AS column_count
        FROM pg_class t
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE t.relkind = 'r'
          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
        """
        if schema_filter:
            sql += " AND n.nspname = %s"
            status, result = self.conn.execute_dict(
                sql, (schema_filter,)
            )
        else:
            status, result = self.conn.execute_dict(sql)

        if not status:
            return []
        return result['rows'] if result else []

    def _fetch_columns(self, schema, name, obj_type):
        if obj_type == 'TABLE':
            sql = """
            SELECT
                a.attname AS name,
                format_type(a.atttypid, a.atttypmod) AS udt_name,
                CASE WHEN a.attnotnull THEN 'NO' ELSE 'YES' END AS is_nullable,
                pg_get_expr(d.adbin, d.adrelid) AS column_default,
                col_description(t.oid, a.attnum) AS description
            FROM pg_class t
            JOIN pg_namespace n ON n.oid = t.relnamespace
            JOIN pg_attribute a ON a.attrelid = t.oid
            LEFT JOIN pg_attrdef d ON d.adrelid = t.oid AND d.adnum = a.attnum
            WHERE t.relname = %s
              AND n.nspname = %s
              AND a.attnum > 0
              AND NOT a.attisdropped
            ORDER BY a.attnum
            """
        else:
            sql = """
            SELECT
                a.attname AS name,
                format_type(a.atttypid, a.atttypmod) AS udt_name,
                col_description(t.oid, a.attnum) AS description
            FROM pg_class t
            JOIN pg_namespace n ON n.oid = t.relnamespace
            JOIN pg_attribute a ON a.attrelid = t.oid
            WHERE t.relname = %s
              AND n.nspname = %s
              AND a.attnum > 0
              AND NOT a.attisdropped
            ORDER BY a.attnum
            """

        status, result = self.conn.execute_dict(sql, (name, schema))
        if not status:
            return []
        return result['rows'] if result else []

    def _fetch_indexes(self, schema, table_name):
        sql = """
        SELECT
            i.relname AS name,
            array_to_string(
                array_agg(a.attname ORDER BY array_position(
                    ix.indkey, a.attnum
                )),
                ', '
            ) AS columns,
            ix.indisunique AS is_unique
        FROM pg_class t
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_index ix ON ix.indrelid = t.oid
        JOIN pg_class i ON i.oid = ix.indexrelid
        JOIN pg_attribute a ON a.attrelid = t.oid
            AND a.attnum = ANY(ix.indkey)
        WHERE t.relname = %s
          AND n.nspname = %s
        GROUP BY i.relname, ix.indisunique
        ORDER BY i.relname
        """
        status, result = self.conn.execute_dict(sql, (table_name, schema))
        if not status:
            return []
        return result['rows'] if result else []

    def _fetch_constraints(self, schema, table_name):
        sql = """
        SELECT
            con.conname AS name,
            con.contype AS constraint_type,
            pg_get_constraintdef(con.oid) AS definition
        FROM pg_constraint con
        JOIN pg_class t ON t.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE t.relname = %s
          AND n.nspname = %s
        ORDER BY con.conname
        """
        status, result = self.conn.execute_dict(sql, (table_name, schema))
        if not status:
            return []
        return result['rows'] if result else []

    def _fetch_triggers(self, schema, table_name):
        sql = """
        SELECT
            tg.tgname AS name,
            CASE
                WHEN tg.tgtype & 1 = 1 THEN 'BEFORE'
                WHEN tg.tgtype & 2 = 2 THEN 'AFTER'
                WHEN tg.tgtype & 64 = 64 THEN 'INSTEAD OF'
                ELSE 'UNKNOWN'
            END AS timing,
            CASE
                WHEN tg.tgtype & 4 = 4 THEN 'INSERT'
                WHEN tg.tgtype & 8 = 8 THEN 'DELETE'
                WHEN tg.tgtype & 16 = 16 THEN 'UPDATE'
                WHEN tg.tgtype & 32 = 32 THEN 'TRUNCATE'
                ELSE 'UNKNOWN'
            END AS event
        FROM pg_trigger tg
        JOIN pg_class t ON t.oid = tg.tgrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE t.relname = %s
          AND n.nspname = %s
          AND NOT tg.tgisinternal
        ORDER BY tg.tgname
        """
        status, result = self.conn.execute_dict(sql, (table_name, schema))
        if not status:
            return []
        return result['rows'] if result else []

    def _fetch_views(self, schema_filter):
        sql = """
        SELECT
            t.oid,
            t.relname AS name,
            n.nspname AS schema,
            obj_description(t.oid, 'pg_class') AS description,
            pg_get_viewdef(t.oid) AS definition
        FROM pg_class t
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE t.relkind = 'v'
          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
        """
        if schema_filter:
            sql += " AND n.nspname = %s"
            status, result = self.conn.execute_dict(
                sql, (schema_filter,)
            )
        else:
            status, result = self.conn.execute_dict(sql)

        if not status:
            return []
        return result['rows'] if result else []

    def _fetch_functions(self, schema_filter):
        sql = """
        SELECT
            p.oid,
            p.proname AS name,
            n.nspname AS schema,
            pg_get_function_result(p.oid) AS return_type,
            obj_description(p.oid, 'pg_proc') AS description,
            pg_get_functiondef(p.oid) AS definition,
            pg_get_function_identity_arguments(p.oid) AS arguments
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
          AND NOT p.prokind = 'a'
        """
        if schema_filter:
            sql += " AND n.nspname = %s"
            status, result = self.conn.execute_dict(
                sql, (schema_filter,)
            )
        else:
            status, result = self.conn.execute_dict(sql)

        if not status:
            return []

        functions = result['rows'] if result else []
        for func in functions:
            args = func.get('arguments', '') or ''
            func['signature'] = (
                f"CREATE FUNCTION {func['schema']}.{func['name']}"
                f"({args})\n"
                f" RETURNS {func.get('return_type', 'void')}"
            )

        return functions