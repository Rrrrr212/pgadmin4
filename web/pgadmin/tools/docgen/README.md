# Database Documentation Generator (docgen)

A pgAdmin 4 tool module that generates comprehensive Markdown documentation
for PostgreSQL databases.

## Overview

The Database Documentation Generator traverses the specified database and
extracts metadata for tables, views, and functions. It produces a structured
Markdown document that includes:

- **Tables**: column details, indexes, constraints, triggers, and comments
- **Views**: column details, view definition, and comments
- **Functions**: return type, arguments, source code, and comments

## Module Structure

```
web/pgadmin/tools/docgen/
├── __init__.py          # Flask Blueprint (DocGenModule) with /generate route
├── engine.py            # DocGenEngine: queries the database, builds Markdown
└── README.md            # This file

web/pgadmin/static/js/tools/docgen/
└── DocGenPanel.jsx      # React component for the UI panel
```

## API Endpoint

### `POST /docgen/generate/<int:sid>/<int:did>`

Generates database documentation.

**URL Parameters:**
- `sid` (int): Server ID
- `did` (int): Database ID

**Request Body (JSON):**
```json
{
    "trans_id": "transaction-id",
    "format": "markdown",
    "include_tables": true,
    "include_views": true,
    "include_functions": true,
    "schema": "public"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trans_id` | string | Yes | Transaction ID for connection management |
| `format` | string | No | Output format (currently only `markdown`) |
| `include_tables` | boolean | No | Include tables in documentation (default: true) |
| `include_views` | boolean | No | Include views in documentation (default: true) |
| `include_functions` | boolean | No | Include functions in documentation (default: true) |
| `schema` | string | No | Filter by schema name (null = all schemas) |

**Response:**
```json
{
    "success": 1,
    "data": {
        "content": "# Database Documentation\n\n...",
        "database": "mydb",
        "format": "markdown"
    }
}
```

## Usage

### From the pgAdmin UI

1. Navigate to a database in the Browser tree
2. Right-click the database and select the Documentation Generator tool
3. Configure the options (schema filter, object types to include)
4. Click **Generate Documentation**
5. Preview the output in the panel
6. Click **Download Markdown** to save the file

### From the Python API

```python
from pgadmin.tools.docgen.engine import DocGenEngine

engine = DocGenEngine(connection)
content = engine.generate(
    output_format='markdown',
    include_tables=True,
    include_views=True,
    include_functions=True,
    schema_filter=None,
)
```

## Registration

To enable this module, add the following entries:

1. **`web/pgadmin/tools/__init__.py`** - Register the blueprint:
   ```python
   from .docgen import blueprint as module
   app.register_blueprint(module)
   ```

2. **`web/pgadmin/tools/user_management/PgAdminPermissions.py`** - Add permission:
   ```python
   tools_docgen = 'tools_docgen'
   ```

## Dependencies

- Flask (Blueprints, routing)
- psycopg (via pgAdmin's `get_driver`)
- React with MUI (for the frontend panel)
- pgAdmin 4 core utilities (`PgAdminModule`, `get_driver`, etc.)