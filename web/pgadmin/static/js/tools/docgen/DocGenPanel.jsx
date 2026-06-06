import React, { useState, useEffect } from 'react';
import { 
  Box, Button, Checkbox, FormControlLabel, FormGroup, 
  Typography, CircularProgress, Select, MenuItem, InputLabel, FormControl 
} from '@mui/material';
import axios from 'axios';
import gettext from 'sources/gettext';

export default function DocGenPanel({ pgBrowser, nodeData }) {
  const [databases, setDatabases] = useState([]);
  const [selectedDb, setSelectedDb] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [options, setOptions] = useState({
    include_tables: true,
    include_views: true,
    include_functions: true,
  });

  // Extract server info from nodeData or pgBrowser context
  const serverId = nodeData?.server_id || pgBrowser?.serverInfo?.id || 1;
  const serverGroupId = nodeData?.server_group_id || 1;

  useEffect(() => {
    // Fetch available databases for the current server
    const fetchDatabases = async () => {
      try {
        const url = `/browser/database/nodes/${serverGroupId}/${serverId}/`;
        const response = await axios.get(url);
        if (response.data && response.data.data) {
          setDatabases(response.data.data);
          if (response.data.data.length > 0) {
            setSelectedDb(response.data.data[0]._id);
          }
        }
      } catch (err) {
        console.error("Failed to fetch databases", err);
      }
    };
    fetchDatabases();
  }, [serverId, serverGroupId]);

  const handleOptionChange = (event) => {
    setOptions({
      ...options,
      [event.target.name]: event.target.checked,
    });
  };

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const url = `/docgen/generate/${serverGroupId}/${serverId}/${selectedDb}`;
      const response = await axios.post(url, options);
      
      const markdown = response.data.data.markdown;
      
      // Trigger download
      const blob = new Blob([markdown], { type: 'text/markdown' });
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      const dbNode = databases.find(db => db._id === selectedDb);
      const dbName = dbNode ? dbNode.label : 'database';
      a.download = `${dbName}_doc.md`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
      
    } catch (err) {
      setError(err.response?.data?.errormsg || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: 3, maxWidth: 600, margin: 'auto' }}>
      <Typography variant="h5" gutterBottom>
        {gettext('Database Document Generator')}
      </Typography>
      
      <FormControl fullWidth sx={{ mb: 3, mt: 2 }}>
        <InputLabel id="database-select-label">{gettext('Select Database')}</InputLabel>
        <Select
          labelId="database-select-label"
          value={selectedDb}
          label={gettext('Select Database')}
          onChange={(e) => setSelectedDb(e.target.value)}
        >
          {databases.map((db) => (
            <MenuItem key={db._id} value={db._id}>
              {db.label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      <Typography variant="h6" gutterBottom>
        {gettext('Include Options')}
      </Typography>
      <FormGroup sx={{ mb: 3 }}>
        <FormControlLabel
          control={
            <Checkbox 
              checked={options.include_tables} 
              onChange={handleOptionChange} 
              name="include_tables" 
            />
          }
          label={gettext('Tables')}
        />
        <FormControlLabel
          control={
            <Checkbox 
              checked={options.include_views} 
              onChange={handleOptionChange} 
              name="include_views" 
            />
          }
          label={gettext('Views')}
        />
        <FormControlLabel
          control={
            <Checkbox 
              checked={options.include_functions} 
              onChange={handleOptionChange} 
              name="include_functions" 
            />
          }
          label={gettext('Functions')}
        />
      </FormGroup>

      {error && (
        <Typography color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      )}

      <Button
        variant="contained"
        color="primary"
        onClick={handleGenerate}
        disabled={loading || !selectedDb}
        startIcon={loading ? <CircularProgress size={20} /> : null}
      >
        {loading ? gettext('Generating...') : gettext('Download Markdown')}
      </Button>
    </Box>
  );
}
