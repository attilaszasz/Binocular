import { useEffect, useState } from "react";
import { Mail, Bell, Send, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { notificationsApi, type NotificationChannel } from "@/lib/api";

export function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saveLoading, setSaveLoading] = useState<string | null>(null);
  const [testLoading, setTestLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Email Config State
  const [emailEnabled, setEmailEnabled] = useState(false);
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState(587);
  const [smtpUser, setSmtpUser] = useState("");
  const [smtpPass, setSmtpPass] = useState("");
  const [smtpUseTls, setSmtpUseTls] = useState(true);
  const [fromEmail, setFromEmail] = useState("");
  const [toEmail, setToEmail] = useState("");
  const [emailMessage, setEmailMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Gotify Config State
  const [gotifyEnabled, setGotifyEnabled] = useState(false);
  const [serverUrl, setServerUrl] = useState("");
  const [appToken, setAppToken] = useState("");
  const [gotifyMessage, setGotifyMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchSettings = async () => {
    await Promise.resolve();
    try {
      setLoading(true);
      setError(null);
      const data = await notificationsApi.list();

      const email = data.find((c) => c.type === "email");
      if (email) {
        setEmailEnabled(email.enabled);
        setSmtpHost((email.config.smtp_host as string) ?? "");
        setSmtpPort((email.config.smtp_port as number) ?? 587);
        setSmtpUser((email.config.smtp_user as string) ?? "");
        setSmtpPass((email.config.smtp_pass as string) ?? "");
        setSmtpUseTls((email.config.smtp_use_tls as boolean) ?? true);
        setFromEmail((email.config.from_email as string) ?? "");
        setToEmail((email.config.to_email as string) ?? "");
      }

      const gotify = data.find((c) => c.type === "gotify");
      if (gotify) {
        setGotifyEnabled(gotify.enabled);
        setServerUrl((gotify.config.server_url as string) ?? "");
        setAppToken((gotify.config.app_token as string) ?? "");
      }
    } catch {
      setError("Failed to load settings configuration.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchSettings();
    }, 0);
    return () => clearTimeout(timer);
  }, []);

  const handleSaveEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveLoading("email");
    setEmailMessage(null);
    try {
      const payload: NotificationChannel = {
        type: "email",
        enabled: emailEnabled,
        config: {
          smtp_host: smtpHost,
          smtp_port: Number(smtpPort),
          smtp_user: smtpUser,
          smtp_pass: smtpPass,
          smtp_use_tls: smtpUseTls,
          from_email: fromEmail,
          to_email: toEmail,
        },
      };
      await notificationsApi.save(payload);
      setEmailMessage({ type: "success", text: "Email configuration saved successfully." });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to save email settings.";
      setEmailMessage({ type: "error", text: msg });
    } finally {
      setSaveLoading(null);
    }
  };

  const handleSaveGotify = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveLoading("gotify");
    setGotifyMessage(null);
    try {
      const payload: NotificationChannel = {
        type: "gotify",
        enabled: gotifyEnabled,
        config: {
          server_url: serverUrl,
          app_token: appToken,
        },
      };
      await notificationsApi.save(payload);
      setGotifyMessage({ type: "success", text: "Gotify configuration saved successfully." });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to save Gotify settings.";
      setGotifyMessage({ type: "error", text: msg });
    } finally {
      setSaveLoading(null);
    }
  };

  const handleTestEmail = async () => {
    setTestLoading("email");
    setEmailMessage(null);
    try {
      await notificationsApi.test({
        type: "email",
        config: {
          smtp_host: smtpHost,
          smtp_port: Number(smtpPort),
          smtp_user: smtpUser,
          smtp_pass: smtpPass,
          smtp_use_tls: smtpUseTls,
          from_email: fromEmail,
          to_email: toEmail,
        },
      });
      setEmailMessage({ type: "success", text: "Test email sent successfully!" });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Test dispatch failed.";
      setEmailMessage({ type: "error", text: msg });
    } finally {
      setTestLoading(null);
    }
  };

  const handleTestGotify = async () => {
    setTestLoading("gotify");
    setGotifyMessage(null);
    try {
      await notificationsApi.test({
        type: "gotify",
        config: {
          server_url: serverUrl,
          app_token: appToken,
        },
      });
      setGotifyMessage({ type: "success", text: "Test Gotify push notification sent successfully!" });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Test dispatch failed.";
      setGotifyMessage({ type: "error", text: msg });
    } finally {
      setTestLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-2">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-muted-foreground text-sm">Loading settings configuration...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Notification Settings</h1>
        <p className="text-muted-foreground mt-1">
          Configure external alert channels to notify you when firmware updates are found.
        </p>
      </div>

      {error && (
        <div className="bg-destructive/10 border border-destructive/20 text-destructive text-sm p-4 rounded-md flex items-center gap-2">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      <div className="grid gap-6">
        {/* Email settings */}
        <Card className="border border-border">
          <CardHeader className="flex flex-row items-start justify-between space-y-0">
            <div className="space-y-1">
              <CardTitle className="flex items-center gap-2">
                <Mail className="h-5 w-5 text-primary" />
                Email / SMTP Alerts
              </CardTitle>
              <CardDescription>
                Deliver responsive HTML alerts via your outgoing SMTP server.
              </CardDescription>
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                id="email-enabled"
                checked={emailEnabled}
                onCheckedChange={setEmailEnabled}
              />
              <Label htmlFor="email-enabled" className="text-sm font-medium">
                {emailEnabled ? "Enabled" : "Disabled"}
              </Label>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSaveEmail} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="smtp-host">SMTP Host</Label>
                  <Input
                    id="smtp-host"
                    value={smtpHost}
                    onChange={(e) => setSmtpHost(e.target.value)}
                    placeholder="e.g. smtp.gmail.com"
                    required={emailEnabled}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="smtp-port">SMTP Port</Label>
                  <Input
                    id="smtp-port"
                    type="number"
                    value={smtpPort}
                    onChange={(e) => setSmtpPort(Number(e.target.value))}
                    placeholder="e.g. 587"
                    required={emailEnabled}
                  />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="smtp-user">SMTP Username</Label>
                  <Input
                    id="smtp-user"
                    value={smtpUser}
                    onChange={(e) => setSmtpUser(e.target.value)}
                    placeholder="e.g. user@gmail.com"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="smtp-pass">SMTP Password / App Password</Label>
                  <Input
                    id="smtp-pass"
                    type="password"
                    value={smtpPass}
                    onChange={(e) => setSmtpPass(e.target.value)}
                    placeholder={smtpPass ? "••••••••" : "Enter password"}
                  />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="from-email">From Email Address</Label>
                  <Input
                    id="from-email"
                    type="email"
                    value={fromEmail}
                    onChange={(e) => setFromEmail(e.target.value)}
                    placeholder="e.g. binocular@example.com"
                    required={emailEnabled}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="to-email">Recipient Email Address</Label>
                  <Input
                    id="to-email"
                    type="email"
                    value={toEmail}
                    onChange={(e) => setToEmail(e.target.value)}
                    placeholder="e.g. operator@example.com"
                    required={emailEnabled}
                  />
                </div>
              </div>

              <div className="flex items-center space-x-2 pt-2">
                <Switch
                  id="smtp-use-tls"
                  checked={smtpUseTls}
                  onCheckedChange={setSmtpUseTls}
                />
                <Label htmlFor="smtp-use-tls">Use SSL/TLS or STARTTLS connection</Label>
              </div>

              {emailMessage && (
                <div
                  className={`p-3 rounded-md text-sm flex items-center gap-2 ${
                    emailMessage.type === "success"
                      ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-500"
                      : "bg-destructive/10 border border-destructive/20 text-destructive"
                  }`}
                >
                  {emailMessage.type === "success" ? (
                    <CheckCircle2 className="h-4 w-4 shrink-0" />
                  ) : (
                    <AlertCircle className="h-4 w-4 shrink-0" />
                  )}
                  <span>{emailMessage.text}</span>
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <Button type="submit" disabled={saveLoading !== null || testLoading !== null}>
                  {saveLoading === "email" ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    "Save Settings"
                  )}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleTestEmail}
                  disabled={saveLoading !== null || testLoading !== null}
                >
                  {testLoading === "email" ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Testing...
                    </>
                  ) : (
                    <>
                      <Send className="mr-2 h-4 w-4" />
                      Test Connection
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Gotify settings */}
        <Card className="border border-border">
          <CardHeader className="flex flex-row items-start justify-between space-y-0">
            <div className="space-y-1">
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5 text-primary" />
                Gotify Push Alerts
              </CardTitle>
              <CardDescription>
                Deliver instant push alerts to your self-hosted Gotify application server.
              </CardDescription>
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                id="gotify-enabled"
                checked={gotifyEnabled}
                onCheckedChange={setGotifyEnabled}
              />
              <Label htmlFor="gotify-enabled" className="text-sm font-medium">
                {gotifyEnabled ? "Enabled" : "Disabled"}
              </Label>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSaveGotify} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="server-url">Gotify Server URL</Label>
                <Input
                  id="server-url"
                  value={serverUrl}
                  onChange={(e) => setServerUrl(e.target.value)}
                  placeholder="e.g. https://gotify.example.com"
                  required={gotifyEnabled}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="app-token">Gotify Application Token</Label>
                <Input
                  id="app-token"
                  type="password"
                  value={appToken}
                  onChange={(e) => setAppToken(e.target.value)}
                  placeholder={appToken ? "••••••••" : "Enter token"}
                  required={gotifyEnabled}
                />
              </div>

              {gotifyMessage && (
                <div
                  className={`p-3 rounded-md text-sm flex items-center gap-2 ${
                    gotifyMessage.type === "success"
                      ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-500"
                      : "bg-destructive/10 border border-destructive/20 text-destructive"
                  }`}
                >
                  {gotifyMessage.type === "success" ? (
                    <CheckCircle2 className="h-4 w-4 shrink-0" />
                  ) : (
                    <AlertCircle className="h-4 w-4 shrink-0" />
                  )}
                  <span>{gotifyMessage.text}</span>
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <Button type="submit" disabled={saveLoading !== null || testLoading !== null}>
                  {saveLoading === "gotify" ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    "Save Settings"
                  )}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleTestGotify}
                  disabled={saveLoading !== null || testLoading !== null}
                >
                  {testLoading === "gotify" ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Testing...
                    </>
                  ) : (
                    <>
                      <Send className="mr-2 h-4 w-4" />
                      Test Connection
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
