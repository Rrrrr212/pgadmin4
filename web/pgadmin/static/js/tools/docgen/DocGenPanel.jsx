/////////////////////////////////////////////////////////////
//
// pgAdmin 4 - PostgreSQL Tools
//
// Copyright (C) 2013 - 2026, The pgAdmin Development Team
// This software is released under the PostgreSQL Licence
//
//////////////////////////////////////////////////////////////
import React, { useState, useCallback } from 'react';
import { styled } from '@mui/material/styles';
import {
  Box, FormControl, FormControlLabel, Switch, InputLabel,
  Select as MuiSelect, MenuItem, FormHelperText, TextField,
  Paper, Typography, CircularProgress,
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import DescriptionIcon from '@mui/icons-material/Description';
import PropTypes from 'prop-types';
import gettext from 'sources/gettext';
import url_for from 'sources/url_for';
import getApiInstance from '../../api_instance';
import { DefaultButton, PrimaryButton } from '../../components/Buttons';
import Loader from '../../components/Loader';

const Root = styled(Box)(({theme}) => ({
  padding: theme.spacing(2),
  height: '100%',
  overflow: 'auto',
  '& .DocGen-header': {
    marginBottom: theme.spacing(2),
  },
  '& .DocGen-section': {
    marginBottom: theme.spacing(3),
  },
  '& .DocGen-preview': {
    marginTop: theme.spacing(2),
    padding: theme.spacing(2),
    backgroundColor: theme.palette.background.paper,
    border: `1px solid ${theme.otherVars.borderColor}`,
    borderRadius: theme.shape.borderRadius,
    maxHeight: '400px',
    overflow: 'auto',
    whiteSpace: 'pre-wrap',
    fontFamily: 'monospace',
    fontSize: '13px',
  },
  '& .DocGen-actions': {
    display: 'flex',
    gap: theme.spacing(1),
    marginTop: theme.spacing(2),
  },
}));

export default function DocGenPanel({ nodeData, node, treeNodeInfo }) {
  const [schemaFilter, setSchemaFilter] = useState('');
  const [includeTables, setIncludeTables] = useState(true);
  const [includeViews, setIncludeViews] = useState(true);
  const [includeFunctions, setIncludeFunctions] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [docContent, setDocContent] = useState('');
  const [error, setError] = useState('');

  const sid = nodeData?.server?._id || nodeData?._id;
  const did = nodeData?._id;

  const handleGenerate = useCallback(() => {
    setGenerating(true);
    setError('');
    setDocContent('');

    const api = getApiInstance();
    const payload = {
      trans_id: treeNodeInfo?.trans_id,
      format: 'markdown',
      include_tables: includeTables,
      include_views: includeViews,
      include_functions: includeFunctions,
      schema: schemaFilter || null,
    };

    api.post(
      url_for('docgen.generate', { sid: sid, did: did }),
      payload
    )
      .then((res) => {
        if (res.data?.success) {
          setDocContent(res.data?.data?.content || '');
          pgAdmin.Browser.notifier.success(
            gettext('Documentation generated successfully.')
          );
        } else {
          setError(res.data?.errormsg || gettext('Failed to generate documentation.'));
        }
      })
      .catch((err) => {
        const msg = err?.response?.data?.errormsg
          || err?.message
          || gettext('An error occurred while generating documentation.');
        setError(msg);
        pgAdmin.Browser.notifier.error(msg);
      })
      .finally(() => {
        setGenerating(false);
      });
  }, [sid, did, includeTables, includeViews, includeFunctions,
    schemaFilter, treeNodeInfo]);

  const handleDownload = useCallback(() => {
    if (!docContent) return;

    const dbName = nodeData?.label || nodeData?.name || 'database';
    const blob = new Blob([docContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${dbName}_documentation.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [docContent, nodeData]);

  return (
    <Root>
      <Box className="DocGen-header">
        <Typography variant="h6">
          <DescriptionIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
          {gettext('Database Documentation Generator')}
        </Typography>
        <Typography variant="body2" color="textSecondary">
          {gettext('Generate Markdown documentation for tables, views, and functions.')}
        </Typography>
      </Box>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Box className="DocGen-section">
          <FormControl fullWidth sx={{ mb: 2 }}>
            <TextField
              label={gettext('Schema Filter (optional)')}
              value={schemaFilter}
              onChange={(e) => setSchemaFilter(e.target.value)}
              helperText={gettext(
                'Leave empty to include all schemas. Example: public'
              )}
              size="small"
            />
          </FormControl>
        </Box>

        <Box className="DocGen-section">
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            {gettext('Include Objects')}
          </Typography>
          <FormControlLabel
            control={
              <Switch
                checked={includeTables}
                onChange={(e) => setIncludeTables(e.target.checked)}
              />
            }
            label={gettext('Tables')}
          />
          <FormControlLabel
            control={
              <Switch
                checked={includeViews}
                onChange={(e) => setIncludeViews(e.target.checked)}
              />
            }
            label={gettext('Views')}
          />
          <FormControlLabel
            control={
              <Switch
                checked={includeFunctions}
                onChange={(e) => setIncludeFunctions(e.target.checked)}
              />
            }
            label={gettext('Functions')}
          />
        </Box>

        <Box className="DocGen-actions">
          <PrimaryButton
            onClick={handleGenerate}
            disabled={generating}
            startIcon={
              generating ? <CircularProgress size={16} /> : <DescriptionIcon />
            }
          >
            {generating
              ? gettext('Generating...')
              : gettext('Generate Documentation')}
          </PrimaryButton>
          <DefaultButton
            onClick={handleDownload}
            disabled={!docContent}
            startIcon={<DownloadIcon />}
          >
            {gettext('Download Markdown')}
          </DefaultButton>
        </Box>
      </Paper>

      {error && (
        <Box sx={{ mt: 2, color: 'error.main' }}>
          <Typography variant="body2">{error}</Typography>
        </Box>
      )}

      {generating && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
          <Loader />
        </Box>
      )}

      {docContent && !generating && (
        <Box className="DocGen-preview">
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            {gettext('Preview')}
          </Typography>
          {docContent}
        </Box>
      )}
    </Root>
  );
}

DocGenPanel.propTypes = {
  nodeData: PropTypes.object,
  node: PropTypes.object,
  treeNodeInfo: PropTypes.object,
};