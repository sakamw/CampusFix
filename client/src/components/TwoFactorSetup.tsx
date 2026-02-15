import { useState } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { useToast } from "../hooks/use-toast";
import { Shield, QrCode, Key } from "lucide-react";

interface TwoFactorSetupProps {
  onComplete: () => void;
  onCancel: () => void;
}

export function TwoFactorSetup({ onComplete, onCancel }: TwoFactorSetupProps) {
  const [step, setStep] = useState<'setup' | 'verify'>('setup');
  const [qrCode, setQrCode] = useState<string>('');
  const [secret, setSecret] = useState<string>('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [verificationCode, setVerificationCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const handleStartSetup = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/auth/2fa/setup/', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setQrCode(data.qr_code);
        setSecret(data.secret);
        setBackupCodes(data.backup_codes);
        setStep('verify');
      }
    } catch (error) {
      toast({
        title: "Setup Failed",
        description: "Failed to generate 2FA setup. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyCode = async () => {
    if (!verificationCode || verificationCode.length !== 6) {
      toast({
        title: "Invalid Code",
        description: "Please enter a 6-digit verification code.",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/auth/2fa/setup/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token: verificationCode }),
      });

      if (response.ok) {
        toast({
          title: "2FA Enabled",
          description: "Two-factor authentication has been successfully enabled.",
        });
        onComplete();
      } else {
        const error = await response.json();
        toast({
          title: "Verification Failed",
          description: error.error || "Invalid verification code.",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Verification Failed",
        description: "Failed to verify code. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (step === 'setup') {
    return (
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Shield className="h-6 w-6 text-primary" />
          </div>
          <CardTitle>Enable Two-Factor Authentication</CardTitle>
          <CardDescription>
            Add an extra layer of security to your account with 2FA
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <h4 className="font-medium">How it works:</h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Scan QR code with your authenticator app</li>
              <li>• Enter 6-digit code to verify setup</li>
              <li>• Use codes for future logins</li>
            </ul>
          </div>
          
          <div className="space-y-2">
            <h4 className="font-medium">Recommended apps:</h4>
            <div className="text-sm text-muted-foreground">
              Google Authenticator, Authy, Microsoft Authenticator
            </div>
          </div>

          <div className="flex gap-2 pt-4">
            <Button variant="outline" onClick={onCancel} className="flex-1">
              Cancel
            </Button>
            <Button onClick={handleStartSetup} disabled={isLoading} className="flex-1">
              {isLoading ? "Generating..." : "Continue Setup"}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
          <QrCode className="h-6 w-6 text-primary" />
        </div>
        <CardTitle>Setup Two-Factor Authentication</CardTitle>
        <CardDescription>
          Scan the QR code and enter the verification code
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {qrCode && (
          <div className="text-center">
            <img 
              src={qrCode} 
              alt="2FA QR Code" 
              className="mx-auto border rounded-lg"
            />
            <p className="text-xs text-muted-foreground mt-2">
              Scan with your authenticator app
            </p>
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="code">Verification Code</Label>
          <Input
            id="code"
            placeholder="000000"
            value={verificationCode}
            onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            className="text-center text-lg tracking-widest"
            maxLength={6}
          />
        </div>

        {secret && (
          <div className="space-y-2">
            <Label>Manual Entry Key</Label>
            <div className="p-2 bg-muted rounded text-xs font-mono break-all">
              {secret}
            </div>
            <p className="text-xs text-muted-foreground">
              Enter this key manually if you can't scan the QR code
            </p>
          </div>
        )}

        {backupCodes.length > 0 && (
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Key className="h-4 w-4" />
              Backup Codes
            </Label>
            <div className="p-3 bg-muted rounded text-xs space-y-1">
              {backupCodes.map((code, index) => (
                <div key={index} className="font-mono">{code}</div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              Save these codes in a safe place. You can use them to access your account if you lose your device.
            </p>
          </div>
        )}

        <div className="flex gap-2">
          <Button variant="outline" onClick={onCancel} className="flex-1">
            Cancel
          </Button>
          <Button 
            onClick={handleVerifyCode} 
            disabled={isLoading || verificationCode.length !== 6} 
            className="flex-1"
          >
            {isLoading ? "Verifying..." : "Enable 2FA"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
