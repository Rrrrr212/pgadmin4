##########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2026, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

"""Database Document Generator Engine - extracts metadata and generates documentation."""

from datetime import datetime
from pgadmin.utils.driver import get_driver
from config import PG_DEFAULT_DRIVER


class DocGenEngine:
    """Engine for extracting database metadata and generating documentation."""

    SQL_TABLES = """
        SELECT
            c.oid,
            n.nspname as schema_name,
            c.relname as table_name,
            pg_catalog.obj_description(c.oid, 'pg_class') as description,
            pg_catalog.pg_get_userbyid(c.relowner) as owner,
            c.reltuples::bigint as estimated_rows
        FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'r'
          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
          AND n.nspname NOT LIKE 'pg_toast%'
          AND n.nspname NOT LIKE 'pg_temp%'
        ORDER BY n.nspname, c.relname;
    """

    SQL_TABLE_COLUMNS = """
        SELECT
            a.attnum as column_id,
            a.attname as column_name,
            pg_catalog.format_type(a.atttypid, a.atttypmod) as data_type,
            a.attnotnull as not_null,
            a.atthasdef as has_default,
            pg_get_expr(d.adbin, d.adrelid) as default_value,
            col_description(c.oid, a.attnum) as description,
            a.attidentity != '' as is_identity,
            a.attgenerated != '' as is_generated
        FROM pg_catalog.pg_attribute a
        JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
        LEFT JOIN pg_catalog.pg_attrdef d ON (a.attrelid, a.attnum) = (d.adrelid, d.adnum)
        WHERE c.oid = %(table_oid)s
          AND a.attnum > 0
          AND NOT a.attisdropped
        ORDER BY a.attnum;
    """

    SQL_TABLE_PK = """
        SELECT
            a.attname as column_name
        FROM pg_catalog.pg_index i
        JOIN pg_catalog.pg_class c ON c.oid = i.indrelid
        JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid AND a.attnum = ANY(i.indkey)
        WHERE c.oid = %(table_oid)s
          AND i.indisprimary
        ORDER BY array_position(i.indkey, a.attnum);
    """

    SQL_TABLE_INDEXES = """
        SELECT
            i.relname as index_name,
            ix.indisunique as is_unique,
            pg_catalog.pg_get_indexdef(ix.indexrelid) as index_definition
        FROM pg_catalog.pg_index ix
        JOIN pg_catalog.pg_class c ON c.oid = ix.indrelid
        JOIN pg_catalog.pg_class i ON i.oid = ix.indexrelid
        WHERE c.oid = %(table_oid)s
          AND ix.indisprimary = false
        ORDER BY i.relname;
    """

    SQL_TABLE_FOREIGN_KEYS = """
        SELECT
            con.conname as constraint_name,
            a1.attname as column_name,
            n2.nspname as foreign_schema,
            c2.relname as foreign_table,
            a2.attname as foreign_column,
            pg_catalog.pg_get_constraintdef(con.oid) as constraint_definition
        FROM pg_catalog.pg_constraint con
        JOIN pg_catalog.pg_class c1 ON c1.oid = con.conrelid
        JOIN pg_catalog.pg_class c2 ON c2.oid = con.confrelid
        JOIN pg_catalog.pg_namespace n2 ON n2.oid = c2.relnamespace
        CROSS JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS k1(attnum, ord)
        CROSS JOIN LATERAL unnest(con.confkey) WITH ORDINALITY AS k2(attnum, ord)
        JOIN pg_catalog.pg_attribute a1 ON a1.attrelid = c1.oid AND a1.attnum = k1.attnum
        JOIN pg_catalog.pg_attribute a2 ON a2.attrelid = c2.oid AND a2.attnum = k2.attnum
        WHERE c1.oid = %(table_oid)s
          AND con.contype = 'f'
        ORDER BY con.conname, k1.ord;
    """

    SQL_VIEWS = """
        SELECT
            c.oid,
            n.nspname as schema_name,
            c.relname as view_name,
            pg_catalog.obj_description(c.oid, 'pg_class') as description,
            pg_catalog.pg_get_userbyid(c.relowner) as owner,
            pg_catalog.pg_get_viewdef(c.oid) as view_definition
        FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind IN ('v', 'm')
          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY n.nspname, c.relname;
    """

    SQL_FUNCTIONS = """
        SELECT
            p.oid,
            n.nspname as schema_name,
            p.proname as function_name,
            pg_catalog.obj_description(p.oid, 'pg_proc') as description,
            pg_catalog.pg_get_userbyid(p.proowner) as owner,
            pg_catalog.pg_get_function_result(p.oid) as return_type,
            pg_catalog.pg_get_function_arguments(p.oid) as arguments,
            CASE p.prokind
                WHEN 'f' THEN 'function'
                WHEN 'p' THEN 'procedure'
                WHEN 'a' THEN 'aggregate'
                WHEN 'w' THEN 'window'
            END as function_type,
            p.prolang::regprocedure as language
        FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY n.nspname, p.proname;
    """

    SQL_SEQUENCES = """
        SELECT
            c.oid,
            n.nspname as schema_name,
            c.relname as sequence_name,
            pg_catalog.obj_description(c.oid, 'pg_class') as description,
            pg_catalog.pg_get_userbyid(c.relowner) as owner,
            s.last_value,
            s.start_value,
            s.increment_by,
            s.max_value,
            s.min_value,
            s.cycle
        FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_catalog.pg_sequences s ON s.schemaname = n.nspname AND s.sequencename = c.relname
        WHERE c.relkind = 'S'
          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY n.nspname, c.relname;
    """

    def __init__(self, sid, did):
        self.sid = sid
        self.did = did

    def _get_connection(self):
        manager = get_driver(PG_DEFAULT_DRIVER).connection_manager(self.sid)
        conn = manager.connection(did=self.did)
        status, msg = conn.connect()
        if not status:
            raise Exception(f"Failed to connect to database: {msg}")
        return conn

    def _execute_query(self, conn, sql, params=None):
        status, result = conn.execute_dict(sql, params)
        if not status:
            raise Exception(f"Query execution failed: {result}")
        return result.get('rows', [])

    def get_tables(self, conn):
        tables = self._execute_query(conn, self.SQL_TABLES)
        for table in tables:
            table['columns'] = self._execute_query(
                conn, self.SQL_TABLE_COLUMNS, {'table_oid': table['oid']}
            )
            table['primary_keys'] = self._execute_query(
                conn, self.SQL_TABLE_PK, {'table_oid': table['oid']}
            )
            table['indexes'] = self._execute_query(
                conn, self.SQL_TABLE_INDEXES, {'table_oid': table['oid']}
            )
            table['foreign_keys'] = self._execute_query(
                conn, self.SQL_TABLE_FOREIGN_KEYS, {'table_oid': table['oid']}
            )
        return tables

    def get_views(self, conn):
        return self._execute_query(conn, self.SQL_VIEWS)

    def get_functions(self, conn):
        return self._execute_query(conn, self.SQL_FUNCTIONS)

    def get_sequences(self, conn):
        return self._execute_query(conn, self.SQL_SEQUENCES)

    def _format_markdown_table(self, headers, rows):
        if not rows:
            return ""
        lines = []
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in rows:
            line = "| " + " | ".join(str(row.get(h.lower().replace(' ', '_'), '')) for h in headers) + " |"
            lines.append(line)
        return "\n".join(lines)

    def _generate_table_section(self, table):
        lines = []
        full_name = f"{table['schema_name']}.{table['table_name']}"
        lines.append(f"### {full_name}")
        lines.append("")

        if table.get('description'):
            lines.append(f"> {table['description']}")
            lines.append("")

        meta_items = []
        if table.get('owner'):
            meta_items.append(f"**Owner**: {table['owner']}")
        if table.get('estimated_rows') is not None:
            meta_items.append(f"**Estimated Rows**: {table['estimated_rows']:,}")
        if meta_items:
            lines.append(" | ".join(meta_items))
            lines.append("")

        if table.get('columns'):
            lines.append("#### Columns")
            lines.append("")
            col_headers = ["#", "Name", "Data Type", "Not Null", "Default", "Description"]
            col_rows = []
            for col in table['columns']:
                pk_names = [pk['column_name'] for pk in table.get('primary_keys', [])]
                name = col['column_name']
                if name in pk_names:
                    name = f"**{name}** 🔑"
                col_rows.append({
                    'column_id': col['column_id'],
                    'name': name,
                    'data_type': col['data_type'],
                    'not_null': 'Yes' if col['not_null'] else 'No',
                    'default': col['default_value'] or '',
                    'description': col['description'] or ''
                })
            lines.append(self._format_markdown_table(col_headers, col_rows))
            lines.append("")

        if table.get('foreign_keys'):
            lines.append("#### Foreign Keys")
            lines.append("")
            fk_headers = ["Constraint", "Column", "References"]
            fk_rows = []
            for fk in table['foreign_keys']:
                ref = f"{fk['foreign_schema']}.{fk['foreign_table']}({fk['foreign_column']})"
                fk_rows.append({
                    'constraint': fk['constraint_name'],
                    'column': fk['column_name'],
                    'references': ref
                })
            lines.append(self._format_markdown_table(fk_headers, fk_rows))
            lines.append("")

        if table.get('indexes'):
            lines.append("#### Indexes")
            lines.append("")
            idx_headers = ["Name", "Unique", "Definition"]
            idx_rows = []
            for idx in table['indexes']:
                idx_rows.append({
                    'name': idx['index_name'],
                    'unique': 'Yes' if idx['is_unique'] else 'No',
                    'definition': f"`{idx['index_definition']}`"
                })
            lines.append(self._format_markdown_table(idx_headers, idx_rows))
            lines.append("")

        lines.append("---")
        lines.append("")
        return "\n".join(lines)

    def _generate_view_section(self, view):
        lines = []
        full_name = f"{view['schema_name']}.{view['view_name']}"
        lines.append(f"### {full_name}")
        lines.append("")

        if view.get('description'):
            lines.append(f"> {view['description']}")
            lines.append("")

        if view.get('owner'):
            lines.append(f"**Owner**: {view['owner']}")
            lines.append("")

        if view.get('view_definition'):
            lines.append("#### Definition")
            lines.append("")
            lines.append("```sql")
            lines.append(view['view_definition'])
            lines.append("```")
            lines.append("")

        lines.append("---")
        lines.append("")
        return "\n".join(lines)

    def _generate_function_section(self, func):
        lines = []
        full_name = f"{func['schema_name']}.{func['function_name']}"
        lines.append(f"### {full_name}")
        lines.append("")

        if func.get('description'):
            lines.append(f"> {func['description']}")
            lines.append("")

        meta_items = []
        if func.get('function_type'):
            meta_items.append(f"**Type**: {func['function_type']}")
        if func.get('return_type'):
            meta_items.append(f"**Returns**: {func['return_type']}")
        if func.get('language'):
            meta_items.append(f"**Language**: {func['language']}")
        if func.get('owner'):
            meta_items.append(f"**Owner**: {func['owner']}")
        if meta_items:
            lines.append(" | ".join(meta_items))
            lines.append("")

        if func.get('arguments'):
            lines.append("#### Arguments")
            lines.append("")
            lines.append(f"```")
            lines.append(f"({func['arguments']})")
            lines.append("```")
            lines.append("")

        lines.append("---")
        lines.append("")
        return "\n".join(lines)

    def _generate_sequence_section(self, seq):
        lines = []
        full_name = f"{seq['schema_name']}.{seq['sequence_name']}"
        lines.append(f"### {full_name}")
        lines.append("")

        if seq.get('description'):
            lines.append(f"> {seq['description']}")
            lines.append("")

        meta_items = []
        if seq.get('owner'):
            meta_items.append(f"**Owner**: {seq['owner']}")
        if seq.get('last_value') is not None:
            meta_items.append(f"**Current Value**: {seq['last_value']}")
        if seq.get('increment_by') is not None:
            meta_items.append(f"**Increment**: {seq['increment_by']}")
        if seq.get('start_value') is not None:
            meta_items.append(f"**Start**: {seq['start_value']}")
        if seq.get('min_value') is not None:
            meta_items.append(f"**Min**: {seq['min_value']}")
        if seq.get('max_value') is not None:
            meta_items.append(f"**Max**: {seq['max_value']}")
        if seq.get('cycle') is not None:
            meta_items.append(f"**Cycle**: {'Yes' if seq['cycle'] else 'No'}")
        if meta_items:
            lines.append(" | ".join(meta_items))
            lines.append("")

        lines.append("---")
        lines.append("")
        return "\n".join(lines)

    def generate_document(self, include_tables=True, include_views=True,
                          include_functions=False, include_sequences=False,
                          output_format='markdown'):
        conn = self._get_connection()

        db_name_sql = "SELECT current_database() as db_name;"
        db_result = self._execute_query(conn, db_name_sql)
        db_name = db_result[0]['db_name'] if db_result else 'unknown'

        version_sql = "SELECT version() as version;"
        version_result = self._execute_query(conn, version_sql)
        db_version = version_result[0]['version'] if version_result else ''

        doc = []
        doc.append(f"# Database Documentation: {db_name}")
        doc.append("")
        doc.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        doc.append("")
        doc.append(f"**Database Version**: {db_version}")
        doc.append("")
        doc.append("---")
        doc.append("")

        doc.append("## Table of Contents")
        doc.append("")

        toc_items = []
        if include_tables:
            toc_items.append("- [Tables](#tables)")
        if include_views:
            toc_items.append("- [Views](#views)")
        if include_functions:
            toc_items.append("- [Functions & Procedures](#functions--procedures)")
        if include_sequences:
            toc_items.append("- [Sequences](#sequences)")
        doc.extend(toc_items)
        doc.append("")
        doc.append("---")
        doc.append("")

        if include_tables:
            doc.append("## Tables")
            doc.append("")
            tables = self.get_tables(conn)
            doc.append(f"**Total Tables**: {len(tables)}")
            doc.append("")
            for table in tables:
                doc.append(self._generate_table_section(table))

        if include_views:
            doc.append("## Views")
            doc.append("")
            views = self.get_views(conn)
            doc.append(f"**Total Views**: {len(views)}")
            doc.append("")
            for view in views:
                doc.append(self._generate_view_section(view))

        if include_functions:
            doc.append("## Functions & Procedures")
            doc.append("")
            functions = self.get_functions(conn)
            doc.append(f"**Total Functions/Procedures**: {len(functions)}")
            doc.append("")
            for func in functions:
                doc.append(self._generate_function_section(func))

        if include_sequences:
            doc.append("## Sequences")
            doc.append("")
            sequences = self.get_sequences(conn)
            doc.append(f"**Total Sequences**: {len(sequences)}")
            doc.append("")
            for seq in sequences:
                doc.append(self._generate_sequence_section(seq))

        return "\n".join(doc)
