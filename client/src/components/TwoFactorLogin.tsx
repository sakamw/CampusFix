import { useState } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { useToast } from "../hooks/use-toast";
import { Shield, Loader2 } from "lucide-react";

interface TwoFactorLoginProps {
  email: string;
  onSuccess: (userData: any) => void;
  onBack: () => void;
}

export function TwoFactorLogin({ email, onSuccess, onBack }: TwoFactorLoginProps) {
  const [code, setCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (code.length !== 6) {
      toast({
        title: "Invalid Code",
        description: "Please enter a 6-digit verification code.",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/auth/2fa/verify/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email,
          token: code,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        
        // Now complete the login with the 2FA verification
        const loginResponse = await fetch('http://localhost:8000/api/auth/login/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email: email,
            password: '', // Password was already verified in previous step
            two_factor_verified: true,
          }),
        });

        if (loginResponse.ok) {
          const loginData = await loginResponse.json();
          localStorage.setItem('access_token', loginData.tokens.access);
          localStorage.setItem('refresh_token', loginData.tokens.refresh);
          onSuccess(loginData.user);
        }
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

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
          <Shield className="h-6 w-6 text-primary" />
        </div>
        <CardTitle>Two-Factor Authentication</CardTitle>
        <CardDescription>
          Enter the 6-digit code from your authenticator app
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="code">Authentication Code</Label>
            <Input
              id="code"
              type="text"
              placeholder="000000"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              className="text-center text-lg tracking-widest"
              maxLength={6}
              autoFocus
            />
          </div>

          <div className="text-center text-sm text-muted-foreground">
            Open your authenticator app and enter the code shown
          </div>

          <div className="space-y-2">
            <Button 
              type="submit" 
              className="w-full" 
              disabled={isLoading || code.length !== 6}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Verifying...
                </>
              ) : (
                'Verify Code'
              )}
            </Button>
            
            <Button 
              type="button" 
              variant="outline" 
              className="w-full"
              onClick={onBack}
            >
              Back to Login
            </Button>
          </div>

          <div className="text-center">
            <Button variant="link" className="text-sm">
              Lost your device? Use backup code
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
