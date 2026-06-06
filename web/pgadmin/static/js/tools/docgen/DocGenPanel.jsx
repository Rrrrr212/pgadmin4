import { useCallback, useEffect, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import { Box, Paper, Typography, styled } from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import RefreshIcon from '@mui/icons-material/Refresh';

import gettext from 'sources/gettext';
import url_for from 'sources/url_for';
import getApiInstance, { parseApiError } from '../../api_instance';
import DownloadUtils from '../../DownloadUtils';
import { DefaultButton, PrimaryButton } from '../../components/Buttons';
import Loader from '../../components/Loader';
import {
  FormFooterMessage,
  FormInputSelect,
  FormNote,
} from '../../components/FormComponents';
import { usePgAdmin } from '../../PgAdminProvider';

const Root = styled(Paper)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  gap: theme.spacing(2),
  padding: theme.spacing(2),
  height: '100%',
  position: 'relative',
  overflow: 'hidden',
}));

const Actions = styled(Box)(({ theme }) => ({
  display: 'flex',
  gap: theme.spacing(1),
  justifyContent: 'flex-end',
  flexWrap: 'wrap',
}));

const Preview = styled(Box)(({ theme }) => ({
  ...theme.mixins.panelBorder.all,
  backgroundColor: theme.palette.background.default,
  borderRadius: theme.shape.borderRadius,
  display: 'flex',
  flexDirection: 'column',
  minHeight: 0,
  overflow: 'hidden',
}));

const PreviewBody = styled(Box)(({ theme }) => ({
  flex: 1,
  overflow: 'auto',
  padding: theme.spacing(2),
  fontFamily: 'monospace',
  fontSize: '0.875rem',
  lineHeight: 1.5,
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
}));

const DEFAULT_FORMAT_OPTIONS = [
  {
    label: gettext('Markdown'),
    value: 'markdown',
  },
];

function normalizeOptions(options = []) {
  return options.map((option) => ({
    label: option.label ?? option.name ?? String(option.value ?? ''),
    value: option.value,
    selected: Boolean(option.selected),
  })).filter((option) => option.label !== '' && option.value !== undefined);
}

function getDefaultDatabase(options, initialDid) {
  if (initialDid !== null && initialDid !== undefined) {
    return initialDid;
  }

  const selectedOption = options.find((option) => option.selected);
  return selectedOption?.value ?? options[0]?.value ?? null;
}

export default function DocGenPanel({
  sgid,
  sid,
  initialDid,
  databaseOptions,
  formatOptions,
  onGenerated,
}) {
  const api = useMemo(() => getApiInstance(), []);
  const pgAdmin = usePgAdmin();
  const [databases, setDatabases] = useState(() =>
    normalizeOptions(databaseOptions)
  );
  const [did, setDid] = useState(() =>
    getDefaultDatabase(normalizeOptions(databaseOptions), initialDid)
  );
  const [format, setFormat] = useState('markdown');
  const [markdown, setMarkdown] = useState('');
  const [filename, setFilename] = useState('database_documentation.md');
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');
  const [busyText, setBusyText] = useState('');
  const [loadingDatabases, setLoadingDatabases] = useState(false);
  const [generating, setGenerating] = useState(false);

  const resolvedFormatOptions =
    normalizeOptions(formatOptions).length > 0 ?
      normalizeOptions(formatOptions) :
      DEFAULT_FORMAT_OPTIONS;

  const notifyError = useCallback((message) => {
    if (pgAdmin?.Browser?.notifier?.error) {
      pgAdmin.Browser.notifier.error(message);
    }
  }, [pgAdmin]);

  const fetchDatabases = useCallback(async () => {
    if (!sgid || !sid) {
      return;
    }

    setLoadingDatabases(true);
    setBusyText(gettext('Loading databases...'));
    setError('');

    try {
      const { data: response } = await api.get(
        url_for('sqleditor.get_new_connection_database', {
          sgid,
          sid,
        })
      );
      const nextOptions = normalizeOptions(response.data?.result?.data || []);
      setDatabases(nextOptions);
      setDid((currentDid) => {
        const hasCurrent = nextOptions.some(
          (option) => String(option.value) === String(currentDid)
        );
        return hasCurrent ? currentDid :
          getDefaultDatabase(nextOptions, initialDid);
      });
    } catch (apiError) {
      const message = parseApiError(apiError);
      setError(message);
      notifyError(message);
    } finally {
      setLoadingDatabases(false);
      setBusyText('');
    }
  }, [api, initialDid, notifyError, sgid, sid]);

  const generateDocument = useCallback(async () => {
    if (!sid || did === null || did === undefined) {
      const message = gettext('Select a database before generating documentation.');
      setError(message);
      return null;
    }

    setGenerating(true);
    setBusyText(gettext('Generating database documentation...'));
    setError('');

    try {
      const { data: response } = await api.post(url_for('docgen.generate'), {
        sid,
        did,
        format,
      });
      const payload = response.data || {};
      setMarkdown(payload.markdown || '');
      setFilename(payload.filename || 'database_documentation.md');
      setSummary(payload.summary || null);
      onGenerated?.(payload);
      return payload;
    } catch (apiError) {
      const message = parseApiError(apiError);
      setError(message);
      notifyError(message);
      return null;
    } finally {
      setGenerating(false);
      setBusyText('');
    }
  }, [api, did, format, notifyError, onGenerated, sid]);

  const handleDownload = useCallback(async () => {
    const payload = markdown ? {
      markdown,
      filename,
    } : await generateDocument();

    if (!payload?.markdown) {
      return;
    }

    DownloadUtils.downloadTextData(
      payload.markdown,
      payload.filename || 'database_documentation.md',
      'text/markdown;charset=utf-8'
    );
  }, [filename, generateDocument, markdown]);

  useEffect(() => {
    const nextOptions = normalizeOptions(databaseOptions);
    if (nextOptions.length === 0) {
      return;
    }

    setDatabases(nextOptions);
    setDid((currentDid) => {
      const hasCurrent = nextOptions.some(
        (option) => String(option.value) === String(currentDid)
      );
      return hasCurrent ? currentDid : getDefaultDatabase(nextOptions, initialDid);
    });
  }, [databaseOptions, initialDid]);

  useEffect(() => {
    if (databaseOptions?.length || !sgid || !sid) {
      return;
    }
    fetchDatabases();
  }, [databaseOptions, fetchDatabases, sgid, sid]);

  useEffect(() => {
    if (!resolvedFormatOptions.some((option) => option.value === format)) {
      setFormat(resolvedFormatOptions[0]?.value || 'markdown');
    }
  }, [format, resolvedFormatOptions]);

  return (
    <Root elevation={0}>
      <Loader message={busyText} />
      <Box>
        <Typography variant="h6">{gettext('Database document generator')}</Typography>
        <Typography variant="body2" color="text.secondary">
          {gettext('Generate Markdown documentation for the selected database, then preview or download it.')}
        </Typography>
      </Box>
      <FormInputSelect
        label={gettext('Database')}
        options={databases}
        value={did}
        onChange={setDid}
        disabled={!sid || loadingDatabases || generating}
        controlProps={{
          allowClear: false,
        }}
      />
      <FormInputSelect
        label={gettext('Format')}
        options={resolvedFormatOptions}
        value={format}
        onChange={setFormat}
        disabled={loadingDatabases || generating}
        controlProps={{
          allowClear: false,
        }}
      />
      <FormNote text={gettext('The generated document includes tables, views, functions, comments, and column metadata from the target database.')} />
      <Actions>
        <DefaultButton
          startIcon={<RefreshIcon />}
          onClick={fetchDatabases}
          disabled={!sgid || !sid || loadingDatabases || generating}
        >
          {gettext('Refresh databases')}
        </DefaultButton>
        <DefaultButton
          onClick={generateDocument}
          disabled={!sid || did === null || did === undefined || loadingDatabases || generating}
        >
          {gettext('Generate')}
        </DefaultButton>
        <PrimaryButton
          startIcon={<DownloadIcon />}
          onClick={handleDownload}
          disabled={!sid || did === null || did === undefined || loadingDatabases || generating}
        >
          {gettext('Download')}
        </PrimaryButton>
      </Actions>
      <FormFooterMessage severity="error" message={error} />
      <Preview>
        <Box sx={{ px: 2, py: 1.5, borderBottom: (theme) => `1px solid ${theme.palette.divider}` }}>
          <Typography variant="subtitle2">
            {summary ? gettext('Preview') : gettext('No document generated yet')}
          </Typography>
          {summary && (
            <Typography variant="body2" color="text.secondary">
              {gettext('Tables: %s, Views: %s, Functions: %s')
                .replace('%s', summary.tables)
                .replace('%s', summary.views)
                .replace('%s', summary.functions)}
            </Typography>
          )}
        </Box>
        <PreviewBody component="pre">
          {markdown || gettext('Select a database and generate a document to preview the Markdown output here.')}
        </PreviewBody>
      </Preview>
    </Root>
  );
}

DocGenPanel.propTypes = {
  sgid: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  sid: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  initialDid: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  databaseOptions: PropTypes.arrayOf(PropTypes.shape({
    label: PropTypes.string,
    value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    selected: PropTypes.bool,
  })),
  formatOptions: PropTypes.arrayOf(PropTypes.shape({
    label: PropTypes.string,
    value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    selected: PropTypes.bool,
  })),
  onGenerated: PropTypes.func,
};

DocGenPanel.defaultProps = {
  sgid: null,
  sid: null,
  initialDid: null,
  databaseOptions: [],
  formatOptions: DEFAULT_FORMAT_OPTIONS,
  onGenerated: undefined,
};
