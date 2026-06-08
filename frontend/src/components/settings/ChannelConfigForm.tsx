import { Mail, Send } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';

interface SMTPSectionProps {
  smtpEnabled: boolean;
  smtpHost: string;
  smtpPort: string;
  smtpUsername: string;
  smtpPassword: string;
  smtpUseTls: boolean;
  mailFrom: string;
  mailTo: string;
  onSmtpEnabledChange: (enabled: boolean) => void;
  onSmtpFieldChange: (field: string, value: string) => void;
  onSmtpUseTlsChange: (useTls: boolean) => void;
  onSave: () => void;
  onTest: () => void;
  isSaving: boolean;
  isTesting: boolean;
}

export function SMTPSection({
  smtpEnabled,
  smtpHost,
  smtpPort,
  smtpUsername,
  smtpPassword,
  smtpUseTls,
  mailFrom,
  mailTo,
  onSmtpEnabledChange,
  onSmtpFieldChange,
  onSmtpUseTlsChange,
  onSave,
  onTest,
  isSaving,
  isTesting,
}: SMTPSectionProps) {
  return (
    <Card className="justify-between">
      <CardHeader className="border-b">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center text-md font-bold text-foreground">
            <Mail className="mr-2 text-primary" size={18} />
            Email / SMTP Channel
          </CardTitle>
          <div className="flex items-center gap-2">
            <Input
              type="checkbox"
              id="smtp-enabled"
              checked={smtpEnabled}
              onChange={(e) => onSmtpEnabledChange(e.target.checked)}
              className="h-4 w-4 shrink-0 rounded"
            />
            <Label htmlFor="smtp-enabled" className="text-xs font-semibold text-muted-foreground cursor-pointer">
              Enabled
            </Label>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="col-span-2 sm:col-span-2">
            <Label htmlFor="smtp-host" className="block text-xs font-medium text-muted-foreground mb-1">
              SMTP Host
            </Label>
            <Input
              id="smtp-host"
              type="text"
              value={smtpHost}
              onChange={(e) => onSmtpFieldChange('smtpHost', e.target.value)}
              placeholder="smtp.gmail.com"
              className="text-xs"
            />
          </div>
          <div>
            <Label htmlFor="smtp-port" className="block text-xs font-medium text-muted-foreground mb-1">
              Port
            </Label>
            <Input
              id="smtp-port"
              type="text"
              value={smtpPort}
              onChange={(e) => onSmtpFieldChange('smtpPort', e.target.value)}
              placeholder="587"
              className="text-xs"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <Label htmlFor="smtp-username" className="block text-xs font-medium text-muted-foreground mb-1">
              Username
            </Label>
            <Input
              id="smtp-username"
              type="text"
              value={smtpUsername}
              onChange={(e) => onSmtpFieldChange('smtpUsername', e.target.value)}
              placeholder="user@gmail.com"
              className="text-xs"
            />
          </div>
          <div>
            <Label htmlFor="smtp-password" className="block text-xs font-medium text-muted-foreground mb-1">
              Password
            </Label>
            <Input
              id="smtp-password"
              type="password"
              value={smtpPassword}
              onChange={(e) => onSmtpFieldChange('smtpPassword', e.target.value)}
              placeholder={smtpPassword === '•' ? '••••••••' : 'Enter Password'}
              className="text-xs"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <Label htmlFor="smtp-mailfrom" className="block text-xs font-medium text-muted-foreground mb-1">
              Mail From
            </Label>
            <Input
              id="smtp-mailfrom"
              type="text"
              value={mailFrom}
              onChange={(e) => onSmtpFieldChange('mailFrom', e.target.value)}
              placeholder="binocular@homelab.lan"
              className="text-xs"
            />
          </div>
          <div>
            <Label htmlFor="smtp-mailto" className="block text-xs font-medium text-muted-foreground mb-1">
              Mail To
            </Label>
            <Input
              id="smtp-mailto"
              type="text"
              value={mailTo}
              onChange={(e) => onSmtpFieldChange('mailTo', e.target.value)}
              placeholder="owner@homelab.lan"
              className="text-xs"
            />
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2">
            <Input
              type="checkbox"
              id="smtp-usetls"
              checked={smtpUseTls}
              onChange={(e) => onSmtpUseTlsChange(e.target.checked)}
              className="h-4 w-4 shrink-0 rounded"
            />
            <Label htmlFor="smtp-usetls" className="text-xs text-muted-foreground cursor-pointer">
              Use Secure TLS / STARTTLS
            </Label>
          </div>
        </div>
      </CardContent>
      <CardFooter className="border-t justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={onTest}
          disabled={isTesting || isSaving}
        >
          {isTesting ? 'Sending Test...' : 'Send Test'}
        </Button>
        <Button
          type="button"
          variant="default"
          onClick={onSave}
          disabled={isTesting || isSaving}
        >
          {isSaving ? 'Saving...' : 'Save Settings'}
        </Button>
      </CardFooter>
    </Card>
  );
}

interface GotifySectionProps {
  gotifyEnabled: boolean;
  gotifyUrl: string;
  gotifyToken: string;
  onGotifyEnabledChange: (enabled: boolean) => void;
  onGotifyFieldChange: (field: string, value: string) => void;
  onSave: () => void;
  onTest: () => void;
  isSaving: boolean;
  isTesting: boolean;
}

export function GotifySection({
  gotifyEnabled,
  gotifyUrl,
  gotifyToken,
  onGotifyEnabledChange,
  onGotifyFieldChange,
  onSave,
  onTest,
  isSaving,
  isTesting,
}: GotifySectionProps) {
  return (
    <Card className="justify-between">
      <CardHeader className="border-b">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center text-md font-bold text-foreground">
            <Send className="mr-2 text-primary" size={18} />
            Gotify Push Channel
          </CardTitle>
          <div className="flex items-center gap-2">
            <Input
              type="checkbox"
              id="gotify-enabled"
              checked={gotifyEnabled}
              onChange={(e) => onGotifyEnabledChange(e.target.checked)}
              className="h-4 w-4 shrink-0 rounded"
            />
            <Label htmlFor="gotify-enabled" className="text-xs font-semibold text-muted-foreground cursor-pointer">
              Enabled
            </Label>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-4">
        <div>
          <Label htmlFor="gotify-url" className="block text-xs font-medium text-muted-foreground mb-1">
            Gotify Server URL
          </Label>
          <Input
            id="gotify-url"
            type="text"
            value={gotifyUrl}
            onChange={(e) => onGotifyFieldChange('gotifyUrl', e.target.value)}
            placeholder="https://gotify.homelab.lan"
            className="text-xs"
          />
        </div>

        <div>
          <Label htmlFor="gotify-token" className="block text-xs font-medium text-muted-foreground mb-1">
            Application Token
          </Label>
          <Input
            id="gotify-token"
            type="password"
            value={gotifyToken}
            onChange={(e) => onGotifyFieldChange('gotifyToken', e.target.value)}
            placeholder={gotifyToken === '•' ? '••••••••' : 'Enter Application Token'}
            className="text-xs"
          />
        </div>
      </CardContent>
      <CardFooter className="border-t justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={onTest}
          disabled={isTesting || isSaving}
        >
          {isTesting ? 'Sending Test...' : 'Send Test'}
        </Button>
        <Button
          type="button"
          variant="default"
          onClick={onSave}
          disabled={isTesting || isSaving}
        >
          {isSaving ? 'Saving...' : 'Save Settings'}
        </Button>
      </CardFooter>
    </Card>
  );
}
