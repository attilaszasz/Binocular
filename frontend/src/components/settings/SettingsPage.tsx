import { useState, useEffect } from 'react';
import { listChannels, configureChannel, testChannel } from '@/api';
import { StatusMessage } from '@/components/settings/StatusMessage';
import { SMTPSection, GotifySection } from '@/components/settings/ChannelConfigForm';

function PageHeader({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight">{title}</h2>
      <p className="mt-1 text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

export function SettingsPage() {
  const [smtpEnabled, setSmtpEnabled] = useState(false);
  const [smtpHost, setSmtpHost] = useState('');
  const [smtpPort, setSmtpPort] = useState('587');
  const [smtpUsername, setSmtpUsername] = useState('');
  const [smtpPassword, setSmtpPassword] = useState('');
  const [smtpUseTls, setSmtpUseTls] = useState(true);
  const [mailFrom, setMailFrom] = useState('');
  const [mailTo, setMailTo] = useState('');

  const [gotifyEnabled, setGotifyEnabled] = useState(false);
  const [gotifyUrl, setGotifyUrl] = useState('');
  const [gotifyToken, setGotifyToken] = useState('');

  const [isLoading, setIsLoading] = useState(true);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [isSmtpSaving, setIsSmtpSaving] = useState(false);
  const [isSmtpTesting, setIsSmtpTesting] = useState(false);
  const [isGotifySaving, setIsGotifySaving] = useState(false);
  const [isGotifyTesting, setIsGotifyTesting] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const channels = await listChannels();
        const smtp = channels.find((c) => c.type === 'smtp');
        if (smtp) {
          setSmtpEnabled(smtp.enabled);
          setSmtpHost(String(smtp.config.smtpHost || smtp.config.smtp_host || ''));
          setSmtpPort(String(smtp.config.smtpPort || smtp.config.smtp_port || '587'));
          setSmtpUsername(String(smtp.config.smtpUsername || smtp.config.smtp_username || ''));
          setSmtpPassword(String(smtp.config.smtpPassword || smtp.config.smtp_password || ''));
          setSmtpUseTls(
            smtp.config.smtpUseTls !== undefined
              ? (smtp.config.smtpUseTls as boolean)
              : smtp.config.smtp_use_tls !== undefined
              ? (smtp.config.smtp_use_tls as boolean)
              : true
          );
          setMailFrom(String(smtp.config.mailFrom || smtp.config.mail_from || ''));
          setMailTo(String(smtp.config.mailTo || smtp.config.mail_to || ''));
        }
        const gotify = channels.find((c) => c.type === 'gotify');
        if (gotify) {
          setGotifyEnabled(gotify.enabled);
          setGotifyUrl(String(gotify.config.gotifyUrl || gotify.config.gotify_url || ''));
          setGotifyToken(String(gotify.config.gotifyToken || gotify.config.gotify_token || ''));
        }
      } catch (err) {
        console.error('Failed to load settings', err);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  async function handleSaveSmtp() {
    setIsSmtpSaving(true);
    setStatusMsg(null);
    try {
      await configureChannel('smtp', {
        enabled: smtpEnabled,
        config: {
          smtpHost,
          smtpPort: parseInt(smtpPort, 10),
          smtpUsername,
          smtpPassword,
          smtpUseTls,
          mailFrom,
          mailTo,
        },
      });
      setStatusMsg({ type: 'success', message: 'SMTP configurations saved successfully!' });
    } catch (err) {
      setStatusMsg({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to save SMTP configurations',
      });
    } finally {
      setIsSmtpSaving(false);
    }
  }

  async function handleTestSmtp() {
    setIsSmtpTesting(true);
    setStatusMsg(null);
    try {
      const resp = await testChannel('smtp', {
        config: {
          smtpHost,
          smtpPort: parseInt(smtpPort, 10),
          smtpUsername,
          smtpPassword,
          smtpUseTls,
          mailFrom,
          mailTo,
        },
      });
      setStatusMsg({ type: 'success', message: resp.detail || 'Test email dispatched successfully!' });
    } catch (err) {
      setStatusMsg({
        type: 'error',
        message: err instanceof Error ? err.message : 'Test email failed to send',
      });
    } finally {
      setIsSmtpTesting(false);
    }
  }

  async function handleSaveGotify() {
    setIsGotifySaving(true);
    setStatusMsg(null);
    try {
      await configureChannel('gotify', {
        enabled: gotifyEnabled,
        config: {
          gotifyUrl,
          gotifyToken,
        },
      });
      setStatusMsg({ type: 'success', message: 'Gotify configurations saved successfully!' });
    } catch (err) {
      setStatusMsg({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to save Gotify configurations',
      });
    } finally {
      setIsGotifySaving(false);
    }
  }

  async function handleTestGotify() {
    setIsGotifyTesting(true);
    setStatusMsg(null);
    try {
      const resp = await testChannel('gotify', {
        config: {
          gotifyUrl,
          gotifyToken,
        },
      });
      setStatusMsg({ type: 'success', message: resp.detail || 'Test push alert dispatched successfully!' });
    } catch (err) {
      setStatusMsg({
        type: 'error',
        message: err instanceof Error ? err.message : 'Test push alert failed to send',
      });
    } finally {
      setIsGotifyTesting(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <p className="text-sm text-muted-foreground">Loading settings...</p>
      </div>
    );
  }

  function handleSmtpFieldChange(field: string, value: string) {
    switch (field) {
      case 'smtpHost':
        setSmtpHost(value);
        break;
      case 'smtpPort':
        setSmtpPort(value);
        break;
      case 'smtpUsername':
        setSmtpUsername(value);
        break;
      case 'smtpPassword':
        setSmtpPassword(value);
        break;
      case 'mailFrom':
        setMailFrom(value);
        break;
      case 'mailTo':
        setMailTo(value);
        break;
    }
  }

  function handleGotifyFieldChange(field: string, value: string) {
    switch (field) {
      case 'gotifyUrl':
        setGotifyUrl(value);
        break;
      case 'gotifyToken':
        setGotifyToken(value);
        break;
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings Configuration"
        description="Configure notification dispatchers, SMTP parameters, and Gotify push alerts."
      />

      {statusMsg !== null && (
        <StatusMessage
          type={statusMsg.type}
          message={statusMsg.message}
          onDismiss={() => setStatusMsg(null)}
        />
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <SMTPSection
          smtpEnabled={smtpEnabled}
          smtpHost={smtpHost}
          smtpPort={smtpPort}
          smtpUsername={smtpUsername}
          smtpPassword={smtpPassword}
          smtpUseTls={smtpUseTls}
          mailFrom={mailFrom}
          mailTo={mailTo}
          onSmtpEnabledChange={setSmtpEnabled}
          onSmtpFieldChange={handleSmtpFieldChange}
          onSmtpUseTlsChange={setSmtpUseTls}
          onSave={handleSaveSmtp}
          onTest={handleTestSmtp}
          isSaving={isSmtpSaving}
          isTesting={isSmtpTesting}
        />

        <GotifySection
          gotifyEnabled={gotifyEnabled}
          gotifyUrl={gotifyUrl}
          gotifyToken={gotifyToken}
          onGotifyEnabledChange={setGotifyEnabled}
          onGotifyFieldChange={handleGotifyFieldChange}
          onSave={handleSaveGotify}
          onTest={handleTestGotify}
          isSaving={isGotifySaving}
          isTesting={isGotifyTesting}
        />
      </div>
    </div>
  );
}
