/////////////////////////////////////////////////////////////
//
// pgAdmin 4 - PostgreSQL Tools
//
// Copyright (C) 2013 - 2026, The pgAdmin Development Team
// This software is released under the PostgreSQL Licence
//
//////////////////////////////////////////////////////////////
import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Button, Select, Checkbox, Box, Typography, Paper, CircularProgress, Alert, Tabs, Tab, Divider, FormControlLabel, FormGroup } from '@mui/material';
import { Download, ContentCopy, Visibility, Settings, Description } from '@mui/icons-material';
import url_for from 'sources/url_for';
import gettext from 'sources/gettext';
import PropTypes from 'prop-types';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

const FORMAT_OPTIONS = [
  { value: 'markdown', label: gettext('Markdown') },
];

export default function DocGenPanel({ params, pgWindow, pgAdmin, panelId, panelDocker }) {
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [schemas, setSchemas] = useState([]);
  const [selectedSchemas, setSelectedSchemas] = useState([]);
  const [format, setFormat] = useState('markdown');
  const [includeSystemObjects, setIncludeSystemObjects] = useState(false);
  const [generatedContent, setGeneratedContent] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [copied, setCopied] = useState(false);
  const contentRef = useRef(null);

  const serverName = params?.server_name || '';
  const databaseName = params?.database_name || '';
  const transId = params?.trans_id;
  const sgid = params?.sgid;
  const sid = params?.sid;
  const did = params?.did;

  useEffect(() => {
    initializeConnection();
  }, []);

  const initializeConnection = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const url = url_for('docgen.initialize', {
        trans_id: transId,
        sgid: sgid,
        sid: sid,
        did: did,
      });

      const response = await pgAdmin.ajax.post(url, JSON.stringify({}));

      if (response.data.success) {
        fetchSchemas();
      } else {
        setError(response.data.result?.errmsg || gettext('Failed to initialize connection'));
      }
    } catch (err) {
      setError(err.message || gettext('Connection initialization failed'));
    } finally {
      setLoading(false);
    }
  }, [transId, sgid, sid, did, pgAdmin]);

  const fetchSchemas = useCallback(async () => {
    try {
      const url = url_for('docgen.generate', {
        trans_id: transId,
        sgid: sgid,
        sid: sid,
        did: did,
      });

      const response = await pgAdmin.ajax.post(url, JSON.stringify({
        format: 'markdown',
        include_system_objects: false,
        selected_schemas: [],
        preview_only: true,
      }));

      if (response.data.success && response.data.data?.schemas) {
        setSchemas(response.data.data.schemas);
        setSelectedSchemas(response.data.data.schemas.map(s => s.name));
      }
    } catch (err) {
      console.error('Failed to fetch schemas:', err);
    }
  }, [transId, sgid, sid, did, pgAdmin]);

  const handleGenerate = useCallback(async () => {
    setGenerating(true);
    setError(null);
    setGeneratedContent(null);

    try {
      const url = url_for('docgen.generate', {
        trans_id: transId,
        sgid: sgid,
        sid: sid,
        did: did,
      });

      const response = await pgAdmin.ajax.post(url, JSON.stringify({
        format: format,
        include_system_objects: includeSystemObjects,
        selected_schemas: selectedSchemas,
      }));

      if (response.data.success) {
        setGeneratedContent(response.data.data.content);
        setActiveTab(0);
      } else {
        setError(response.data.errormsg || gettext('Failed to generate documentation'));
      }
    } catch (err) {
      setError(err.message || gettext('Documentation generation failed'));
    } finally {
      setGenerating(false);
    }
  }, [transId, sgid, sid, did, format, includeSystemObjects, selectedSchemas, pgAdmin]);

  const handleDownload = useCallback(async () => {
    try {
      const url = url_for('docgen.download', {
        trans_id: transId,
        sgid: sgid,
        sid: sid,
        did: did,
      });

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          format: format,
          include_system_objects: includeSystemObjects,
          selected_schemas: selectedSchemas,
        }),
      });

      if (response.ok) {
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `${databaseName || 'database'}_documentation.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);
      } else {
        setError(gettext('Failed to download documentation'));
      }
    } catch (err) {
      setError(err.message || gettext('Download failed'));
    }
  }, [transId, sgid, sid, did, format, includeSystemObjects, selectedSchemas, databaseName]);

  const handleCopyToClipboard = useCallback(() => {
    if (generatedContent) {
      navigator.clipboard.writeText(generatedContent).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  }, [generatedContent]);

  const handleSchemaToggle = useCallback((schemaName) => {
    setSelectedSchemas(prev => {
      if (prev.includes(schemaName)) {
        return prev.filter(s => s !== schemaName);
      }
      return [...prev, schemaName];
    });
  }, []);

  const handleSelectAllSchemas = useCallback(() => {
    if (selectedSchemas.length === schemas.length) {
      setSelectedSchemas([]);
    } else {
      setSelectedSchemas(schemas.map(s => s.name));
    }
  }, [schemas, selectedSchemas]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>{gettext('Initializing...')}</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', p: 2 }}>
      <Typography variant="h6" gutterBottom>
        {gettext('Database Documentation Generator')}
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" gutterBottom>
          <Settings fontSize="small" sx={{ mr: 1, verticalAlign: 'middle' }} />
          {gettext('Configuration')}
        </Typography>
        <Divider sx={{ mb: 2 }} />

        <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
          <Box sx={{ minWidth: 200 }}>
            <Typography variant="body2" gutterBottom>
              {gettext('Output Format')}
            </Typography>
            <Select
              value={format}
              onChange={(e) => setFormat(e.target.value)}
              size="small"
              fullWidth
              displayEmpty
            >
              {FORMAT_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </Select>
          </Box>

          <Box>
            <Typography variant="body2" gutterBottom>
              {gettext('Options')}
            </Typography>
            <FormGroup>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={includeSystemObjects}
                    onChange={(e) => setIncludeSystemObjects(e.target.checked)}
                    size="small"
                  />
                }
                label={gettext('Include system objects')}
              />
            </FormGroup>
          </Box>
        </Box>

        {schemas.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" gutterBottom>
              {gettext('Schemas')}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', maxHeight: 150, overflow: 'auto' }}>
              <Button
                size="small"
                variant="outlined"
                onClick={handleSelectAllSchemas}
              >
                {selectedSchemas.length === schemas.length ? gettext('Deselect All') : gettext('Select All')}
              </Button>
              {schemas.map(schema => (
                <Button
                  key={schema.name}
                  size="small"
                  variant={selectedSchemas.includes(schema.name) ? 'contained' : 'outlined'}
                  onClick={() => handleSchemaToggle(schema.name)}
                >
                  {schema.name}
                </Button>
              ))}
            </Box>
          </Box>
        )}

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="contained"
            color="primary"
            onClick={handleGenerate}
            disabled={generating || selectedSchemas.length === 0}
            startIcon={generating ? <CircularProgress size={20} /> : <Description />}
          >
            {generating ? gettext('Generating...') : gettext('Generate Documentation')}
          </Button>

          {generatedContent && (
            <>
              <Button
                variant="outlined"
                onClick={handleDownload}
                startIcon={<Download />}
              >
                {gettext('Download')}
              </Button>
              <Button
                variant="outlined"
                onClick={handleCopyToClipboard}
                startIcon={<ContentCopy />}
              >
                {copied ? gettext('Copied!') : gettext('Copy to Clipboard')}
              </Button>
            </>
          )}
        </Box>
      </Paper>

      {generatedContent && (
        <Paper sx={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)} sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tab icon={<Visibility />} label={gettext('Preview')} />
            <Tab icon={<Description />} label={gettext('Source')} />
          </Tabs>

          <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
            {activeTab === 0 ? (
              <Box className="markdown-body" ref={contentRef}>
                <ReactMarkdown
                  children={generatedContent}
                  components={{
                    code({ node, inline, className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || '');
                      return !inline && match ? (
                        <SyntaxHighlighter
                          children={String(children).replace(/\n$/, '')}
                          style={vscDarkPlus}
                          language={match[1]}
                          PreTag="div"
                          {...props}
                        />
                      ) : (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      );
                    }
                  }}
                />
              </Box>
            ) : (
              <Box component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                {generatedContent}
              </Box>
            )}
          </Box>
        </Paper>
      )}

      {!generatedContent && !generating && (
        <Paper sx={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', flexDirection: 'column', p: 4 }}>
          <Description sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="body1" color="text.secondary">
            {gettext('Configure options and click "Generate Documentation" to create database documentation')}
          </Typography>
        </Paper>
      )}
    </Box>
  );
}

DocGenPanel.propTypes = {
  params: PropTypes.object.isRequired,
  pgWindow: PropTypes.object.isRequired,
  pgAdmin: PropTypes.object.isRequired,
  panelId: PropTypes.string.isRequired,
  panelDocker: PropTypes.object.isRequired,
};
