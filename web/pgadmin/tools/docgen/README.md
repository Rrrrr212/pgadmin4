# Database Document Generator (docgen)

A pgAdmin 4 tool for automatically generating comprehensive database documentation in Markdown format.

## Overview

The Database Document Generator traverses a specified PostgreSQL database and extracts metadata about tables, views, functions, and sequences. It then produces well-formatted Markdown documentation that includes:

- **Tables**: Column definitions, data types, constraints, primary keys, foreign keys, and indexes
- **Views**: View definitions and descriptions
- **Functions & Procedures**: Signatures, return types, arguments, and descriptions
- **Sequences**: Current values, increment settings, and bounds

## File Structure

```
web/pgadmin/tools/docgen/
├── __init__.py          # Flask Blueprint and route definitions
├── engine.py            # Database metadata extraction and Markdown generation engine
├── README.md            # This documentation file
└── static/
    └── js/
        └── DocGenPanel.jsx  # React UI component

web/pgadmin/static/js/tools/docgen/
└── DocGenPanel.jsx      # Re-export proxy for the React component
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tools/docgen/generate/<sid>/<did>` | POST | Generate documentation for the specified database |
| `/tools/docgen/preview/<sid>/<did>` | POST | Preview documentation without downloading |
| `/tools/docgen/databases/<sid>` | GET | List available databases on a server |

### Generate/Preview Request Body

```json
{
  "include_tables": true,
  "include_views": true,
  "include_functions": false,
  "include_sequences": false,
  "output_format": "markdown"
}
```

### Response Format

```json
{
  "success": 1,
  "data": {
    "content": "# Database Documentation: mydb\n...",
    "format": "markdown"
  }
}
```

## Usage

### Via pgAdmin UI

1. Connect to a PostgreSQL server in pgAdmin
2. Navigate to **Tools** > **Database Document Generator**
3. Select a database from the tree
4. Configure options:
   - **Include Tables**: Include table definitions with columns, keys, and indexes
   - **Include Views**: Include view definitions
   - **Include Functions**: Include function and procedure signatures
   - **Include Sequences**: Include sequence configurations
   - **Output Format**: Choose Markdown or Plain Text
5. Click **Preview** to see the generated documentation
6. Click **Download** to save the documentation file

### Via API

```bash
# Generate documentation for database did=12345 on server sid=1
curl -X POST http://localhost:5050/tools/docgen/generate/1/12345 \
  -H "Content-Type: application/json" \
  -d '{
    "include_tables": true,
    "include_views": true,
    "include_functions": true,
    "include_sequences": true,
    "output_format": "markdown"
  }'
```

## Registration

To enable this module, ensure it is registered in `web/pgadmin/tools/__init__.py`:

```python
from .docgen import blueprint as module
app.register_blueprint(module)
```

## Output Example

```markdown
# Database Documentation: mydb

**Generated**: 2026-06-06 10:30:00

**Database Version**: PostgreSQL 16.2 on x86_64-pc-linux-gnu

---

## Table of Contents

- [Tables](#tables)
- [Views](#views)

---

## Tables

**Total Tables**: 3

### public.users

> Stores user account information

**Owner**: postgres | **Estimated Rows**: 1,234

#### Columns

| # | Name | Data Type | Not Null | Default | Description |
|---|------|-----------|----------|---------|-------------|
| 1 | **id** 🔑 | integer | Yes | nextval('users_id_seq') | Unique identifier |
| 2 | username | varchar(100) | Yes | | User login name |
| 3 | email | varchar(255) | Yes | | User email address |

#### Foreign Keys

| Constraint | Column | References |
|------------|--------|------------|
| fk_users_role | role_id | public.roles(id) |

#### Indexes

| Name | Unique | Definition |
|------|--------|------------|
| idx_users_email | Yes | CREATE UNIQUE INDEX ... |

---
```

## Dependencies

- **Backend**: Flask, psycopg (via pgAdmin's driver layer)
- **Frontend**: React, MUI (Material-UI), react-markdown

## Security

- All endpoints require authentication (`@pga_login_required`)
- Database access uses pgAdmin's existing connection management
- Only databases the user has access to can be documented

## Troubleshooting

### "Could not find the required server"
Ensure the server ID (sid) is valid and the server exists in pgAdmin.

### "Failed to connect to database"
Check that the database connection is active and credentials are correct.

### Empty documentation
Verify that the database contains objects of the selected types (tables, views, etc.). System schemas (`pg_catalog`, `information_schema`) are excluded by default.
