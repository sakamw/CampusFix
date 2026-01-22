import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { GraduationCap, Eye, EyeOff, Loader2, ArrowLeft, Mail, KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { authApi } from "@/lib/api";

export default function ForgotPassword() {
  const [searchParams] = useSearchParams();
  const tokenFromUrl = searchParams.get("token");
  
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [resetToken, setResetToken] = useState(tokenFromUrl || "");
  const [showResetForm, setShowResetForm] = useState(!!tokenFromUrl);
  
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleRequestReset = async (e: React.FormEvent) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const email = (form.querySelector('#email') as HTMLInputElement)?.value;

    if (!email) {
      toast({
        title: "Error",
        description: "Please enter your email address",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    const result = await authApi.forgotPassword(email);
    setIsLoading(false);

    if (result.data) {
      setEmailSent(true);
      // In dev mode, we get the token back for testing
      if (result.data.reset_token) {
        setResetToken(result.data.reset_token);
      }
      toast({
        title: "Email Sent",
        description: "Check your email for password reset instructions",
      });
    } else {
      toast({
        title: "Error",
        description: result.error || "Failed to send reset email",
        variant: "destructive",
      });
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const token = (form.querySelector('#token') as HTMLInputElement)?.value;
    const password = (form.querySelector('#password') as HTMLInputElement)?.value;
    const confirmPassword = (form.querySelector('#confirmPassword') as HTMLInputElement)?.value;

    if (!token || !password || !confirmPassword) {
      toast({
        title: "Error",
        description: "Please fill in all fields",
        variant: "destructive",
      });
      return;
    }

    if (password !== confirmPassword) {
      toast({
        title: "Error",
        description: "Passwords do not match",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    const result = await authApi.resetPassword(token, password, confirmPassword);
    setIsLoading(false);

    if (result.data) {
      toast({
        title: "Success",
        description: "Your password has been reset successfully",
      });
      navigate("/login");
    } else {
      toast({
        title: "Error",
        description: result.error || "Failed to reset password",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 gradient-hero items-center justify-center p-12">
        <div className="max-w-md text-center animate-fade-in">
          <div className="mb-8 flex justify-center">
            <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-accent shadow-lg">
              <GraduationCap className="h-10 w-10 text-accent-foreground" />
            </div>
          </div>
          <h1 className="text-4xl font-bold text-primary-foreground mb-4">
            CampusFix
          </h1>
          <p className="text-lg text-primary-foreground/80 leading-relaxed">
            Don't worry, it happens to the best of us. Let's get you back into your account.
          </p>
        </div>
      </div>

      {/* Right side - Form */}
      <div className="flex w-full lg:w-1/2 items-center justify-center p-8">
        <div className="w-full max-w-md animate-slide-up">
          <div className="lg:hidden mb-8 text-center">
            <div className="mb-4 flex justify-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-primary">
                <GraduationCap className="h-7 w-7 text-primary-foreground" />
              </div>
            </div>
            <h1 className="text-2xl font-bold">CampusFix</h1>
          </div>

          {!showResetForm && !emailSent && (
            <div className="space-y-6">
              <div className="space-y-2 text-center">
                <div className="flex justify-center mb-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
                    <Mail className="h-8 w-8 text-primary" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold">Forgot Password?</h2>
                <p className="text-muted-foreground">
                  Enter your email address and we'll send you a link to reset your password.
                </p>
              </div>

              <form onSubmit={handleRequestReset} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email Address</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="email@university.edu"
                    className="input-focus"
                  />
                </div>

                <Button type="submit" className="w-full" size="lg" disabled={isLoading}>
                  {isLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  Send Reset Link
                </Button>
              </form>

              <div className="text-center">
                <Link
                  to="/login"
                  className="inline-flex items-center text-sm text-primary hover:underline"
                >
                  <ArrowLeft className="h-4 w-4 mr-1" />
                  Back to Sign In
                </Link>
              </div>
            </div>
          )}

          {emailSent && !showResetForm && (
            <div className="space-y-6">
              <div className="space-y-2 text-center">
                <div className="flex justify-center mb-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
                    <Mail className="h-8 w-8 text-green-600 dark:text-green-400" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold">Check Your Email</h2>
                <p className="text-muted-foreground">
                  We've sent a password reset link to your email address.
                </p>
              </div>

              <div className="bg-muted/50 rounded-lg p-4 text-center">
                <p className="text-sm text-muted-foreground mb-2">
                  Didn't receive the email? Check your spam folder or
                </p>
                <Button
                  variant="link"
                  className="p-0 h-auto"
                  onClick={() => setEmailSent(false)}
                >
                  try again with a different email
                </Button>
              </div>

              {/* Dev mode: Show reset form button when token is available */}
              {resetToken && (
                <div className="border-t pt-4">
                  <p className="text-xs text-muted-foreground text-center mb-2">
                    Development Mode: Token received
                  </p>
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => setShowResetForm(true)}
                  >
                    Continue to Reset Password
                  </Button>
                </div>
              )}

              <div className="text-center">
                <Link
                  to="/login"
                  className="inline-flex items-center text-sm text-primary hover:underline"
                >
                  <ArrowLeft className="h-4 w-4 mr-1" />
                  Back to Sign In
                </Link>
              </div>
            </div>
          )}

          {showResetForm && (
            <div className="space-y-6">
              <div className="space-y-2 text-center">
                <div className="flex justify-center mb-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
                    <KeyRound className="h-8 w-8 text-primary" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold">Reset Password</h2>
                <p className="text-muted-foreground">
                  Enter your new password below.
                </p>
              </div>

              <form onSubmit={handleResetPassword} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="token">Reset Token</Label>
                  <Input
                    id="token"
                    type="text"
                    defaultValue={resetToken}
                    placeholder="Paste your reset token"
                    className="input-focus font-mono text-sm"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">New Password</Label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      placeholder="••••••••"
                      className="pr-10 input-focus"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm New Password</Label>
                  <div className="relative">
                    <Input
                      id="confirmPassword"
                      type={showConfirmPassword ? "text" : "password"}
                      placeholder="••••••••"
                      className="pr-10 input-focus"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showConfirmPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>

                <Button type="submit" className="w-full" size="lg" disabled={isLoading}>
                  {isLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  Reset Password
                </Button>
              </form>

              <div className="text-center">
                <Link
                  to="/login"
                  className="inline-flex items-center text-sm text-primary hover:underline"
                >
                  <ArrowLeft className="h-4 w-4 mr-1" />
                  Back to Sign In
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
