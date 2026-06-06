def generate_database_markdown(conn, options=None):
    if options is None:
        options = {}
    
    include_tables = options.get('include_tables', True)
    include_views = options.get('include_views', True)
    include_functions = options.get('include_functions', True)
    
    md = []
    
    status, result = conn.execute_dict("""
        SELECT current_database() as dbname;
    """)
    if not status:
        raise Exception(f"Error getting database name: {result}")
        
    dbname = result['rows'][0]['dbname']
    
    md.append(f"# Database Documentation: {dbname}\n")
    
    # Get all schemas
    status, schemas_result = conn.execute_dict("""
        SELECT nspname, obj_description(oid, 'pg_namespace') as comment
        FROM pg_namespace
        WHERE nspname NOT LIKE 'pg_%' AND nspname != 'information_schema'
        ORDER BY nspname;
    """)
    if not status:
        raise Exception(f"Error getting schemas: {schemas_result}")
        
    for schema_row in schemas_result['rows']:
        schema_name = schema_row['nspname']
        schema_comment = schema_row['comment'] or ''
        
        md.append(f"## Schema: {schema_name}")
        if schema_comment:
            md.append(f"{schema_comment}\n")
            
        if include_tables:
            status, tables_result = conn.execute_dict(
                "SELECT c.relname, obj_description(c.oid, 'pg_class') as comment "
                "FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE c.relkind IN ('r', 'p') AND n.nspname = %s "
                "ORDER BY c.relname;",
                [schema_name]
            )
            if tables_result['rows']:
                md.append(f"### Tables\n")
                for table_row in tables_result['rows']:
                    table_name = table_row['relname']
                    table_comment = table_row['comment'] or ''
                    
                    md.append(f"#### Table: `{table_name}`")
                    if table_comment:
                        md.append(f"**Description**: {table_comment}\n")
                        
                    status, columns_result = conn.execute_dict(
                        "SELECT a.attname, "
                        "       pg_catalog.format_type(a.atttypid, a.atttypmod) as type, "
                        "       col_description(a.attrelid, a.attnum) as comment "
                        "FROM pg_attribute a "
                        "JOIN pg_class c ON c.oid = a.attrelid "
                        "JOIN pg_namespace n ON n.oid = c.relnamespace "
                        "WHERE a.attnum > 0 AND NOT a.attisdropped "
                        "  AND c.relname = %s AND n.nspname = %s "
                        "ORDER BY a.attnum;",
                        [table_name, schema_name]
                    )
                    
                    if columns_result['rows']:
                        md.append("| Column | Type | Description |")
                        md.append("|---|---|---|")
                        for col_row in columns_result['rows']:
                            col_name = col_row['attname']
                            col_type = col_row['type']
                            col_comment = col_row['comment'] or ''
                            col_comment = col_comment.replace('|', '\\|').replace('\n', ' ')
                            md.append(f"| {col_name} | {col_type} | {col_comment} |")
                        md.append("\n")

        if include_views:
            status, views_result = conn.execute_dict(
                "SELECT c.relname, obj_description(c.oid, 'pg_class') as comment "
                "FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE c.relkind IN ('v', 'm') AND n.nspname = %s "
                "ORDER BY c.relname;",
                [schema_name]
            )
            if views_result['rows']:
                md.append(f"### Views\n")
                for view_row in views_result['rows']:
                    view_name = view_row['relname']
                    view_comment = view_row['comment'] or ''
                    md.append(f"#### View: `{view_name}`")
                    if view_comment:
                        md.append(f"**Description**: {view_comment}\n")
                    md.append("\n")

        if include_functions:
            status, functions_result = conn.execute_dict(
                "SELECT p.proname, "
                "       pg_catalog.pg_get_function_arguments(p.oid) as args, "
                "       pg_catalog.pg_get_function_result(p.oid) as result_type, "
                "       obj_description(p.oid, 'pg_proc') as comment "
                "FROM pg_proc p "
                "JOIN pg_namespace n ON n.oid = p.pronamespace "
                "WHERE n.nspname = %s "
                "ORDER BY p.proname;",
                [schema_name]
            )
            if functions_result['rows']:
                md.append(f"### Functions\n")
                for func_row in functions_result['rows']:
                    func_name = func_row['proname']
                    func_args = func_row['args']
                    func_result = func_row['result_type']
                    func_comment = func_row['comment'] or ''
                    
                    md.append(f"#### Function: `{func_name}({func_args}) -> {func_result}`")
                    if func_comment:
                        md.append(f"**Description**: {func_comment}\n")
                    md.append("\n")
                        
    return "\n".join(md)
