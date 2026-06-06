##########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2026, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

"""Database documentation generation engine."""
from datetime import datetime


class DocGenEngine:
    """Engine to extract database metadata and generate documentation."""

    def __init__(self, conn, include_system_objects=False, selected_schemas=None):
        """
        Initialize the documentation generator engine.

        Args:
            conn: Database connection object
            include_system_objects: Whether to include system schemas
            selected_schemas: List of schema names to include (None for all)
        """
        self.conn = conn
        self.include_system_objects = include_system_objects
        self.selected_schemas = selected_schemas

    def _execute_query(self, sql):
        """
        Execute a SQL query and return results.

        Args:
            sql: SQL query string

        Returns:
            tuple: (status, result)
        """
        status, result = self.conn.execute_dict(sql)
        return status, result

    def _get_schemas(self):
        """
        Get list of schemas in the database.

        Returns:
            list: List of schema dictionaries
        """
        sql = """
            SELECT n.oid, n.nspname AS name,
                   pg_catalog.obj_description(n.oid, 'pg_namespace') AS description
            FROM pg_catalog.pg_namespace n
            WHERE n.nspname NOT IN ('pg_toast', 'pg_toast_temp')
        """

        if not self.include_system_objects:
            sql += """
              AND n.nspname NOT LIKE 'pg_%'
              AND n.nspname != 'information_schema'
            """

        if self.selected_schemas:
            schema_list = "', '".join(self.selected_schemas)
            sql += f" AND n.nspname IN ('{schema_list}')"

        sql += " ORDER BY n.nspname"

        status, result = self._execute_query(sql)
        if status:
            return result.get('rows', [])
        return []

    def _get_tables(self, schema_oid):
        """
        Get list of tables in a schema.

        Args:
            schema_oid: Schema OID

        Returns:
            list: List of table dictionaries
        """
        sql = f"""
            SELECT c.oid, c.relname AS name,
                   pg_catalog.obj_description(c.oid, 'pg_class') AS description,
                   c.reltuples::bigint AS row_count,
                   pg_catalog.pg_size_pretty(pg_catalog.pg_table_size(c.oid)) AS size
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.oid = {schema_oid}
              AND c.relkind = 'r'
            ORDER BY c.relname
        """

        status, result = self._execute_query(sql)
        if status:
            return result.get('rows', [])
        return []

    def _get_views(self, schema_oid):
        """
        Get list of views in a schema.

        Args:
            schema_oid: Schema OID

        Returns:
            list: List of view dictionaries
        """
        sql = f"""
            SELECT c.oid, c.relname AS name,
                   pg_catalog.obj_description(c.oid, 'pg_class') AS description,
                   pg_get_viewdef(c.oid, true) AS definition
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.oid = {schema_oid}
              AND c.relkind IN ('v', 'm')
            ORDER BY c.relname
        """

        status, result = self._execute_query(sql)
        if status:
            return result.get('rows', [])
        return []

    def _get_columns(self, table_oid):
        """
        Get column information for a table or view.

        Args:
            table_oid: Table/view OID

        Returns:
            list: List of column dictionaries
        """
        sql = f"""
            SELECT a.attnum AS position,
                   a.attname AS name,
                   pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
                   a.attnotnull AS not_null,
                   a.atthasdef AS has_default,
                   pg_get_expr(ad.adbin, ad.adrelid) AS default_value,
                   col_description(a.attrelid, a.attnum) AS description,
                   a.attisdropped AS is_dropped
            FROM pg_catalog.pg_attribute a
            LEFT JOIN pg_catalog.pg_attrdef ad ON a.attrelid = ad.adrelid AND a.attnum = ad.adnum
            WHERE a.attrelid = {table_oid}
              AND a.attnum > 0
              AND NOT a.attisdropped
            ORDER BY a.attnum
        """

        status, result = self._execute_query(sql)
        if status:
            return result.get('rows', [])
        return []

    def _get_constraints(self, table_oid):
        """
        Get constraint information for a table.

        Args:
            table_oid: Table OID

        Returns:
            list: List of constraint dictionaries
        """
        sql = f"""
            SELECT con.conname AS name,
                   CASE con.contype
                       WHEN 'p' THEN 'PRIMARY KEY'
                       WHEN 'u' THEN 'UNIQUE'
                       WHEN 'f' THEN 'FOREIGN KEY'
                       WHEN 'c' THEN 'CHECK'
                       WHEN 't' THEN 'TRIGGER'
                       ELSE con.contype::text
                   END AS type,
                   pg_get_constraintdef(con.oid) AS definition
            FROM pg_catalog.pg_constraint con
            WHERE con.conrelid = {table_oid}
            ORDER BY con.contype, con.conname
        """

        status, result = self._execute_query(sql)
        if status:
            return result.get('rows', [])
        return []

    def _get_indexes(self, table_oid):
        """
        Get index information for a table.

        Args:
            table_oid: Table OID

        Returns:
            list: List of index dictionaries
        """
        sql = f"""
            SELECT i.indexrelid AS oid,
                   c.relname AS name,
                   pg_get_indexdef(i.indexrelid) AS definition,
                   i.indisunique AS is_unique,
                   i.indisprimary AS is_primary
            FROM pg_catalog.pg_index i
            JOIN pg_catalog.pg_class c ON c.oid = i.indexrelid
            WHERE i.indrelid = {table_oid}
            ORDER BY c.relname
        """

        status, result = self._execute_query(sql)
        if status:
            return result.get('rows', [])
        return []

    def _get_functions(self, schema_oid):
        """
        Get list of functions in a schema.

        Args:
            schema_oid: Schema OID

        Returns:
            list: List of function dictionaries
        """
        sql = f"""
            SELECT p.oid, p.proname AS name,
                   pg_catalog.obj_description(p.oid, 'pg_proc') AS description,
                   pg_catalog.pg_get_function_result(p.oid) AS return_type,
                   pg_catalog.pg_get_function_arguments(p.oid) AS arguments,
                   l.lanname AS language,
                   p.prosrc AS source
            FROM pg_catalog.pg_proc p
            JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
            JOIN pg_catalog.pg_language l ON l.oid = p.prolang
            WHERE n.oid = {schema_oid}
              AND p.prokind = 'f'
            ORDER BY p.proname
        """

        status, result = self._execute_query(sql)
        if status:
            return result.get('rows', [])
        return []

    def _get_sequences(self, schema_oid):
        """
        Get list of sequences in a schema.

        Args:
            schema_oid: Schema OID

        Returns:
            list: List of sequence dictionaries
        """
        sql = f"""
            SELECT c.oid, c.relname AS name,
                   pg_catalog.obj_description(c.oid, 'pg_class') AS description,
                   seq.start_value,
                   seq.increment,
                   seq.min_value,
                   seq.max_value,
                   seq.last_value
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_catalog.pg_sequences seq ON seq.schemaname = n.nspname AND seq.sequencename = c.relname
            WHERE n.oid = {schema_oid}
              AND c.relkind = 'S'
            ORDER BY c.relname
        """

        status, result = self._execute_query(sql)
        if status:
            return result.get('rows', [])
        return []

    def _format_markdown_table(self, headers, rows):
        """
        Format data as a Markdown table.

        Args:
            headers: List of column headers
            rows: List of row dictionaries

        Returns:
            str: Markdown table string
        """
        if not rows:
            return "_No data available_\n"

        header_row = "| " + " | ".join(headers) + " |"
        separator = "| " + " | ".join(["---"] * len(headers)) + " |"

        data_rows = []
        for row in rows:
            values = [str(row.get(h.lower().replace(" ", "_"), "")) or "" for h in headers]
            data_rows.append("| " + " | ".join(values) + " |")

        return "\n".join([header_row, separator] + data_rows) + "\n"

    def _generate_table_documentation(self, table, schema_name):
        """
        Generate documentation for a single table.

        Args:
            table: Table dictionary
            schema_name: Schema name

        Returns:
            str: Markdown documentation for the table
        """
        doc = []
        doc.append(f"#### Table: `{table['name']}`\n")

        if table.get('description'):
            doc.append(f"> {table['description']}\n")

        if table.get('row_count') is not None:
            doc.append(f"- **Estimated Rows:** {table['row_count']:,}")
        if table.get('size'):
            doc.append(f"- **Size:** {table['size']}")

        doc.append("")

        columns = self._get_columns(table['oid'])
        if columns:
            doc.append("**Columns:**\n")
            col_headers = ["Position", "Name", "Data Type", "Not Null", "Default", "Description"]
            col_rows = []
            for col in columns:
                col_rows.append({
                    'position': str(col['position']),
                    'name': f"`{col['name']}`",
                    'data_type': col['data_type'],
                    'not_null': "Yes" if col['not_null'] else "No",
                    'default': col['default_value'] or "",
                    'description': col['description'] or ""
                })
            doc.append(self._format_markdown_table(col_headers, col_rows))

        constraints = self._get_constraints(table['oid'])
        if constraints:
            doc.append("**Constraints:**\n")
            con_headers = ["Name", "Type", "Definition"]
            con_rows = []
            for con in constraints:
                con_rows.append({
                    'name': f"`{con['name']}`",
                    'type': con['type'],
                    'definition': f"`{con['definition']}`"
                })
            doc.append(self._format_markdown_table(con_headers, con_rows))

        indexes = self._get_indexes(table['oid'])
        if indexes:
            doc.append("**Indexes:**\n")
            idx_headers = ["Name", "Unique", "Definition"]
            idx_rows = []
            for idx in indexes:
                idx_rows.append({
                    'name': f"`{idx['name']}`",
                    'unique': "Yes" if idx['is_unique'] else "No",
                    'definition': f"`{idx['definition'][:100]}{'...' if len(str(idx['definition'])) > 100 else ''}`"
                })
            doc.append(self._format_markdown_table(idx_headers, idx_rows))

        doc.append("---\n")
        return "\n".join(doc)

    def _generate_view_documentation(self, view, schema_name):
        """
        Generate documentation for a single view.

        Args:
            view: View dictionary
            schema_name: Schema name

        Returns:
            str: Markdown documentation for the view
        """
        doc = []
        doc.append(f"#### View: `{view['name']}`\n")

        if view.get('description'):
            doc.append(f"> {view['description']}\n")

        columns = self._get_columns(view['oid'])
        if columns:
            doc.append("**Columns:**\n")
            col_headers = ["Position", "Name", "Data Type", "Description"]
            col_rows = []
            for col in columns:
                col_rows.append({
                    'position': str(col['position']),
                    'name': f"`{col['name']}`",
                    'data_type': col['data_type'],
                    'description': col['description'] or ""
                })
            doc.append(self._format_markdown_table(col_headers, col_rows))

        if view.get('definition'):
            doc.append("**Definition:**\n")
            doc.append("```sql")
            doc.append(view['definition'])
            doc.append("```\n")

        doc.append("---\n")
        return "\n".join(doc)

    def _generate_function_documentation(self, function, schema_name):
        """
        Generate documentation for a single function.

        Args:
            function: Function dictionary
            schema_name: Schema name

        Returns:
            str: Markdown documentation for the function
        """
        doc = []
        doc.append(f"#### Function: `{function['name']}`\n")

        if function.get('description'):
            doc.append(f"> {function['description']}\n")

        doc.append(f"- **Language:** {function['language']}")
        doc.append(f"- **Returns:** `{function['return_type']}`")

        if function.get('arguments'):
            doc.append(f"- **Arguments:** `{function['arguments']}`")

        doc.append("")

        if function.get('source'):
            doc.append("**Source:**\n")
            doc.append("```sql")
            doc.append(function['source'][:500])
            if len(str(function['source'])) > 500:
                doc.append("...")
            doc.append("```\n")

        doc.append("---\n")
        return "\n".join(doc)

    def _generate_sequence_documentation(self, sequence, schema_name):
        """
        Generate documentation for a single sequence.

        Args:
            sequence: Sequence dictionary
            schema_name: Schema name

        Returns:
            str: Markdown documentation for the sequence
        """
        doc = []
        doc.append(f"#### Sequence: `{sequence['name']}`\n")

        if sequence.get('description'):
            doc.append(f"> {sequence['description']}\n")

        doc.append("| Property | Value |")
        doc.append("|---|---|")

        if sequence.get('start_value') is not None:
            doc.append(f"| Start Value | {sequence['start_value']} |")
        if sequence.get('increment') is not None:
            doc.append(f"| Increment | {sequence['increment']} |")
        if sequence.get('min_value') is not None:
            doc.append(f"| Min Value | {sequence['min_value']} |")
        if sequence.get('max_value') is not None:
            doc.append(f"| Max Value | {sequence['max_value']} |")
        if sequence.get('last_value') is not None:
            doc.append(f"| Last Value | {sequence['last_value']} |")

        doc.append("")
        doc.append("---\n")
        return "\n".join(doc)

    def generate(self, format_type='markdown'):
        """
        Generate documentation for the database.

        Args:
            format_type: Output format (currently only 'markdown' supported)

        Returns:
            str: Generated documentation content
        """
        if format_type != 'markdown':
            format_type = 'markdown'

        doc = []

        doc.append("# Database Documentation\n")
        doc.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        doc.append(f"**Database:** {self.conn.db}\n")
        doc.append(f"**Server Version:** {self.conn.manager.version}\n")

        doc.append("---\n")

        schemas = self._get_schemas()

        if not schemas:
            doc.append("\n_No schemas found in this database.\n")
            return "\n".join(doc)

        doc.append(f"\n## Summary\n")
        doc.append(f"| Schema | Tables | Views | Functions | Sequences |")
        doc.append(f"|---|---|---|---|---|")

        schema_data = []
        for schema in schemas:
            tables = self._get_tables(schema['oid'])
            views = self._get_views(schema['oid'])
            functions = self._get_functions(schema['oid'])
            sequences = self._get_sequences(schema['oid'])

            schema_data.append({
                'schema': schema,
                'tables': tables,
                'views': views,
                'functions': functions,
                'sequences': sequences
            })

            doc.append(
                f"| {schema['name']} | {len(tables)} | {len(views)} | "
                f"{len(functions)} | {len(sequences)} |"
            )

        doc.append("\n---\n")

        for data in schema_data:
            schema = data['schema']
            doc.append(f"\n## Schema: `{schema['name']}`\n")

            if schema.get('description'):
                doc.append(f"> {schema['description']}\n")

            tables = data['tables']
            if tables:
                doc.append(f"\n### Tables ({len(tables)})\n")
                for table in tables:
                    doc.append(self._generate_table_documentation(table, schema['name']))

            views = data['views']
            if views:
                doc.append(f"\n### Views ({len(views)})\n")
                for view in views:
                    doc.append(self._generate_view_documentation(view, schema['name']))

            functions = data['functions']
            if functions:
                doc.append(f"\n### Functions ({len(functions)})\n")
                for func in functions:
                    doc.append(self._generate_function_documentation(func, schema['name']))

            sequences = data['sequences']
            if sequences:
                doc.append(f"\n### Sequences ({len(sequences)})\n")
                for seq in sequences:
                    doc.append(self._generate_sequence_documentation(seq, schema['name']))

            doc.append("\n---\n")

        doc.append("\n*Documentation generated by pgAdmin Database Documentation Generator*\n")

        return "\n".join(doc)
