# Database Document Generator (docgen)

The docgen module provides functionality to generate Markdown documentation for a specified PostgreSQL database.

## Features

- Traverses tables, views, and functions.
- Extracts comments, columns, data types, and other schema information.
- Outputs a clean Markdown file.
- React-based frontend panel for selecting the database, choosing options, and downloading the documentation.

## File Structure

- `web/pgadmin/tools/docgen/__init__.py`: Flask Blueprint and route `/docgen/generate`.
- `web/pgadmin/tools/docgen/engine.py`: Core logic for extracting schema info and generating Markdown.
- `web/pgadmin/static/js/tools/docgen/DocGenPanel.jsx`: React component for the UI.
- `web/pgadmin/tools/docgen/README.md`: This file.

## How to Use

1. Register the `docgen` blueprint in the main application.
2. In pgAdmin, navigate to the DocGen Panel.
3. Select a database, check desired format options, and click **Download Markdown**.
