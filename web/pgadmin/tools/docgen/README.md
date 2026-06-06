# Database Document Generator

The `docgen` tool generates Markdown documentation for a selected PostgreSQL database.

## Files

- `__init__.py` exposes the Flask blueprint and the `/docgen/generate` route.
- `engine.py` connects to the target database, inspects tables, views, and functions, and renders Markdown output.
- `../../static/js/tools/docgen/DocGenPanel.jsx` provides a React panel for selecting a database, generating documentation, previewing the result, and downloading the Markdown file.

## Request format

Send a `POST` request to `/docgen/generate` with a JSON payload similar to the following:

```json
{
  "sid": 1,
  "did": 7,
  "format": "markdown",
  "include_tables": true,
  "include_views": true,
  "include_functions": true
}
```

## Response format

The endpoint returns a JSON payload containing:

- `database`: database name
- `server`: server name
- `filename`: suggested Markdown filename
- `markdown`: generated Markdown document
- `summary`: counts for tables, views, and functions

## Frontend usage

Render `DocGenPanel` with a server group id and server id so it can load the available databases automatically:

```jsx
<DocGenPanel sgid={1} sid={12} />
```

You can also provide database options directly:

```jsx
<DocGenPanel
  sid={12}
  databaseOptions={[
    { label: 'postgres', value: 1, selected: true },
    { label: 'app_db', value: 2 },
  ]}
/>
```

## Generated content

The Markdown output includes:

- database overview metadata
- tables and views grouped by schema
- column name, type, nullability, default value, and column comment
- functions and procedures with signature, return type, language, and comment
