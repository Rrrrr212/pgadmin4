/////////////////////////////////////////////////////////////
//
// pgAdmin 4 - PostgreSQL Tools
//
// Copyright (C) 2013 - 2026, The pgAdmin Development Team
// This software is released under the PostgreSQL Licence
//
//////////////////////////////////////////////////////////////
import React, { useState, useCallback, useRef, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Box, Typography, Paper, FormControlLabel, Checkbox, FormGroup, FormControl, InputLabel, Select, MenuItem, Divider } from '@mui/material';
import { styled } from '@mui/material/styles';
import DownloadIcon from '@mui/icons-material/Download';
import PreviewIcon from '@mui/icons-material/Visibility';
import GenerateIcon from '@mui/icons-material/AutoAwesome';
import getApiInstance, { parseApiError } from '../../../../../static/js/api_instance';
import url_for from 'sources/url_for';
import gettext from 'sources/gettext';
import { PrimaryButton } from '../../../../../static/js/components/Buttons';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';

const StyledContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  padding: '16px',
  overflow: 'auto',
  background: theme.palette.background.default,
}));

const OptionsPanel = styled(Paper)(({ theme }) => ({
  padding: '16px',
  marginBottom: '16px',
  background: theme.palette.background.paper,
  border: `1px solid ${theme.palette.divider}`,
}));

const PreviewPanel = styled(Paper)(({ theme }) => ({
  padding: '24px',
  flex: 1,
  overflow: 'auto',
  background: theme.palette.background.paper,
  border: `1px solid ${theme.palette.divider}`,
  '& h1': {
    fontSize: '2em',
    marginBottom: '0.5em',
    borderBottom: `1px solid ${theme.palette.divider}`,
    paddingBottom: '0.3em',
  },
  '& h2': {
    fontSize: '1.5em',
    marginTop: '1em',
    marginBottom: '0.5em',
    borderBottom: `1px solid ${theme.palette.divider}`,
    paddingBottom: '0.3em',
  },
  '& h3': {
    fontSize: '1.25em',
    marginTop: '1em',
    marginBottom: '0.5em',
  },
  '& h4': {
    fontSize: '1.1em',
    marginTop: '0.8em',
    marginBottom: '0.4em',
  },
  '& table': {
    borderCollapse: 'collapse',
    width: '100%',
    marginBottom: '1em',
    '& th, & td': {
      border: `1px solid ${theme.palette.divider}`,
      padding: '8px 12px',
      textAlign: 'left',
    },
    '& th': {
      background: theme.palette.action.hover,
      fontWeight: 'bold',
    },
  },
  '& blockquote': {
    borderLeft: `4px solid ${theme.palette.primary.main}`,
    paddingLeft: '16px',
    margin: '1em 0',
    color: theme.palette.text.secondary,
    fontStyle: 'italic',
  },
  '& code': {
    background: theme.palette.action.hover,
    padding: '2px 6px',
    borderRadius: '4px',
    fontFamily: 'monospace',
    fontSize: '0.9em',
  },
  '& pre': {
    background: theme.palette.action.hover,
    padding: '16px',
    borderRadius: '4px',
    overflow: 'auto',
    '& code': {
      background: 'none',
      padding: 0,
    },
  },
  '& hr': {
    border: 'none',
    borderTop: `1px solid ${theme.palette.divider}`,
    margin: '2em 0',
  },
  '& a': {
    color: theme.palette.primary.main,
    textDecoration: 'none',
    '&:hover': {
      textDecoration: 'underline',
    },
  },
}));

const Toolbar = styled(Box)(({ theme }) => ({
  display: 'flex',
  gap: '8px',
  marginBottom: '16px',
  alignItems: 'center',
}));

const EmptyState = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  flex: 1,
  color: theme.palette.text.secondary,
  '& svg': {
    fontSize: '64px',
    marginBottom: '16px',
    opacity: 0.3,
  },
}));

export default function DocGenPanel({ params }) {
  const api = useMemo(() => getApiInstance(), []);
  const [options, setOptions] = useState({
    include_tables: true,
    include_views: true,
    include_functions: false,
    include_sequences: false,
    output_format: 'markdown',
  });
  const [docContent, setDocContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const previewRef = useRef(null);

  const sgid = params?.sgid;
  const sid = params?.sid;
  const did = params?.did;

  const handleOptionChange = useCallback((key, value) => {
    setOptions((prev) => ({
      ...prev,
      [key]: value,
    }));
  }, []);

  const handleGenerate = useCallback(async () => {
    if (!sid || !did) {
      setError(gettext('Please select a database first.'));
      return;
    }

    setLoading(true);
    setError('');
    setDocContent('');

    try {
      const url = url_for('docgen.generate', { sid, did });
      const response = await api.post(url, options);
      if (response.data.success) {
        setDocContent(response.data.data.content);
      } else {
        setError(response.data.errormsg || gettext('Failed to generate document.'));
      }
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, [api, sid, did, options]);

  const handlePreview = useCallback(async () => {
    if (!sid || !did) {
      setError(gettext('Please select a database first.'));
      return;
    }

    setLoading(true);
    setError('');

    try {
      const url = url_for('docgen.preview', { sid, did });
      const response = await api.post(url, options);
      if (response.data.success) {
        setDocContent(response.data.data.content);
      } else {
        setError(response.data.errormsg || gettext('Failed to preview document.'));
      }
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, [api, sid, did, options]);

  const handleDownload = useCallback(() => {
    if (!docContent) {
      setError(gettext('No document to download. Please generate a document first.'));
      return;
    }

    const extension = options.output_format === 'markdown' ? 'md' : 'txt';
    const mimeType = options.output_format === 'markdown' ? 'text/markdown' : 'text/plain';
    const blob = new Blob([docContent], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `database_documentation.${extension}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [docContent, options.output_format]);

  if (loading) {
    return (
      <StyledContainer>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1 }}>
          <Typography>{gettext('Generating document...')}</Typography>
        </Box>
      </StyledContainer>
    );
  }

  return (
    <StyledContainer>
      <Typography variant="h5" gutterBottom>
        {gettext('Database Document Generator')}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {gettext('Generate comprehensive documentation for your database including tables, views, functions, and sequences.')}
      </Typography>

      <OptionsPanel elevation={0}>
        <Typography variant="subtitle1" gutterBottom>
          {gettext('Options')}
        </Typography>
        <Divider sx={{ mb: 2 }} />
        <FormGroup row>
          <FormControlLabel
            control={
              <Checkbox
                checked={options.include_tables}
                onChange={(e) => handleOptionChange('include_tables', e.target.checked)}
              />
            }
            label={gettext('Include Tables')}
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={options.include_views}
                onChange={(e) => handleOptionChange('include_views', e.target.checked)}
              />
            }
            label={gettext('Include Views')}
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={options.include_functions}
                onChange={(e) => handleOptionChange('include_functions', e.target.checked)}
              />
            }
            label={gettext('Include Functions')}
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={options.include_sequences}
                onChange={(e) => handleOptionChange('include_sequences', e.target.checked)}
              />
            }
            label={gettext('Include Sequences')}
          />
        </FormGroup>
        <Box sx={{ mt: 2 }}>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>{gettext('Output Format')}</InputLabel>
            <Select
              value={options.output_format}
              label={gettext('Output Format')}
              onChange={(e) => handleOptionChange('output_format', e.target.value)}
            >
              <MenuItem value="markdown">{gettext('Markdown')}</MenuItem>
              <MenuItem value="text">{gettext('Plain Text')}</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </OptionsPanel>

      <Toolbar>
        <PrimaryButton
          variant="contained"
          color="primary"
          startIcon={<GenerateIcon />}
          onClick={handleGenerate}
          disabled={!sid || !did}
        >
          {gettext('Generate')}
        </PrimaryButton>
        <PrimaryButton
          variant="outlined"
          startIcon={<PreviewIcon />}
          onClick={handlePreview}
          disabled={!sid || !did}
        >
          {gettext('Preview')}
        </PrimaryButton>
        <PrimaryButton
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={handleDownload}
          disabled={!docContent}
        >
          {gettext('Download')}
        </PrimaryButton>
      </Toolbar>

      {error && (
        <Typography color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      )}

      {docContent ? (
        <PreviewPanel elevation={0} ref={previewRef}>
          <ReactMarkdown
            rehypePlugins={[rehypeRaw, rehypeSanitize]}
          >
            {docContent}
          </ReactMarkdown>
        </PreviewPanel>
      ) : (
        <EmptyState>
          <GenerateIcon />
          <Typography variant="h6">{gettext('No Document Generated')}</Typography>
          <Typography variant="body2">
            {gettext('Configure options above and click Generate to create database documentation.')}
          </Typography>
        </EmptyState>
      )}
    </StyledContainer>
  );
}

DocGenPanel.propTypes = {
  params: PropTypes.object,
};
