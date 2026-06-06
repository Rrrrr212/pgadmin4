# Database Documentation Generator

A pgAdmin 4 module for automatically generating comprehensive database documentation in Markdown format.

## Features

- **Automatic Schema Discovery**: Scans all schemas, tables, views, functions, and sequences
- **Rich Metadata Extraction**: Captures comments, column types, constraints, indexes, and more
- **Markdown Output**: Generates clean, well-formatted Markdown documentation
- **Schema Filtering**: Select specific schemas to include in the documentation
- **System Object Filtering**: Option to include or exclude system schemas
- **Download & Copy**: Download as `.md` file or copy to clipboard
- **Live Preview**: Preview generated documentation before downloading

## Installation

The module is included in the `web/pgadmin/tools/docgen/` directory. To enable it:

1. Ensure the module is registered in pgAdmin's module system
2. Restart pgAdmin server
3. The module will appear in the Tools menu

## Usage

### Accessing the Tool

1. Open pgAdmin 4
2. Navigate to **Tools** > **Database Documentation Generator**
3. Select a database to generate documentation for

### Configuration Options

- **Output Format**: Currently supports Markdown format
- **Include System Objects**: Toggle to include/exclude PostgreSQL system schemas (`pg_catalog`, `information_schema`, etc.)
- **Schema Selection**: Choose which schemas to include in the documentation

### Generating Documentation

1. Configure the options as needed
2. Select the schemas you want to document
3. Click **Generate Documentation**
4. Preview the output in the built-in viewer
5. Download or copy the documentation

### Downloading

- Click **Download** to save the documentation as a `.md` file
- Click **Copy to Clipboard** to copy the raw Markdown content

## Generated Documentation Structure

The generated documentation includes:

### Summary Table
- Overview of all schemas with counts of tables, views, functions, and sequences

### Per-Schema Documentation
For each schema:

#### Tables
- Table name and description
- Estimated row count and size
- Column details (name, data type, nullable, default value, description)
- Constraints (primary keys, unique, foreign keys, check constraints)
- Indexes (name, uniqueness, definition)

#### Views
- View name and description
- Column details
- View definition (SQL)

#### Functions
- Function name and description
- Language and return type
- Arguments
- Source code (truncated for large functions)

#### Sequences
- Sequence name and description
- Start value, increment, min/max values, last value

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/docgen/panel/<trans_id>` | POST | Render the documentation generator panel |
| `/docgen/initialize/<trans_id>/<sgid>/<sid>/<did>` | POST | Initialize connection to database |
| `/docgen/generate/<trans_id>/<sgid>/<sid>/<did>` | POST | Generate documentation |
| `/docgen/download/<trans_id>/<sgid>/<sid>/<did>` | POST | Generate and download documentation |

## Architecture

### Backend (`web/pgadmin/tools/docgen/`)

- `__init__.py`: Flask Blueprint definition and route handlers
- `engine.py`: `DocGenEngine` class that queries PostgreSQL system catalogs and generates Markdown

### Frontend (`web/pgadmin/static/js/tools/docgen/`)

- `DocGenPanel.jsx`: React component providing the UI for configuration, generation, preview, and download

## PostgreSQL System Catalogs Used

The engine queries the following PostgreSQL system catalogs:

- `pg_namespace`: Schema information
- `pg_class`: Tables, views, sequences
- `pg_attribute`: Column definitions
- `pg_constraint`: Constraints
- `pg_index`: Indexes
- `pg_proc`: Functions
- `pg_sequences`: Sequence metadata

## Requirements

- pgAdmin 4
- PostgreSQL 10+ (for full feature support)
- Modern web browser with JavaScript enabled

## License

This module is released under the PostgreSQL Licence, consistent with pgAdmin 4.
