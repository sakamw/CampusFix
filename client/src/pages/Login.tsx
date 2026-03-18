import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { GraduationCap, Eye, EyeOff, Loader2, MailCheck } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../components/ui/tabs";
import { useToast } from "../hooks/use-toast";
import { useAuth } from "../contexts/AuthContext";
import { getAuthRedirectPath, getRegisterRedirectPath } from "../utils/auth";

export default function Login() {
  const [showPassword, setShowPassword] = useState(false);
  const [showRegPassword, setShowRegPassword] = useState(false);
  const [showRegConfirmPassword, setShowRegConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();
  const { login, register } = useAuth();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const email = (form.querySelector("#email") as HTMLInputElement)?.value;
    const password = (form.querySelector("#password") as HTMLInputElement)
      ?.value;

    if (!email || !password) {
      toast({
        title: "Error",
        description: "Please fill in all required fields",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    const result = await login(email, password);
    setIsLoading(false);

    if (result.success) {
      toast({
        title: "Success",
        description: "Logged in successfully",
      });

      const redirectPath = getAuthRedirectPath(location, result.user);
      navigate(redirectPath);
    } else {
      toast({
        title: "Error",
        description: result.error || "Invalid email or password",
        variant: "destructive",
      });
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const firstName = (form.querySelector("#firstName") as HTMLInputElement)
      ?.value;
    const lastName = (form.querySelector("#lastName") as HTMLInputElement)
      ?.value;
    const studentId = (form.querySelector("#studentId") as HTMLInputElement)
      ?.value;
    const email = (form.querySelector("#regEmail") as HTMLInputElement)?.value;
    const password = (form.querySelector("#regPassword") as HTMLInputElement)
      ?.value;
    const confirmPassword = (
      form.querySelector("#confirmPassword") as HTMLInputElement
    )?.value;

    if (
      !firstName ||
      !lastName ||
      !studentId ||
      !email ||
      !password ||
      !confirmPassword
    ) {
      toast({
        title: "Error",
        description: "Please fill in all required fields",
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
    const result = await register({
      email,
      first_name: firstName,
      last_name: lastName,
      student_id: studentId,
      password,
      password_confirm: confirmPassword,
    });
    setIsLoading(false);

    if (result.success) {
      setRegisteredEmail(email);
      toast({
        title: "Registration Successful",
        description: "Please check your email for an activation link.",
      });
    } else {
      toast({
        title: "Error",
        description: result.error || "Registration failed",
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
            Your intelligent campus issue reporting system. Report, track, and
            resolve campus issues efficiently.
          </p>
          <div className="mt-12 grid grid-cols-3 gap-4 text-center">
            <div className="rounded-lg bg-primary-foreground/10 p-4">
              <p className="text-2xl font-bold text-primary-foreground">
                2.5k+
              </p>
              <p className="text-sm text-primary-foreground/70">
                Issues Resolved
              </p>
            </div>
            <div className="rounded-lg bg-primary-foreground/10 p-4">
              <p className="text-2xl font-bold text-primary-foreground">98%</p>
              <p className="text-sm text-primary-foreground/70">Satisfaction</p>
            </div>
            <div className="rounded-lg bg-primary-foreground/10 p-4">
              <p className="text-2xl font-bold text-primary-foreground">24h</p>
              <p className="text-sm text-primary-foreground/70">Avg Response</p>
            </div>
          </div>
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

          <Tabs defaultValue="login" className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-6">
              <TabsTrigger value="login">Sign In</TabsTrigger>
              <TabsTrigger value="register">Register</TabsTrigger>
            </TabsList>

            {registeredEmail ? (
              <div className="bg-card border rounded-xl p-8 text-center space-y-4 animate-in fade-in zoom-in duration-300">
                <div className="flex justify-center">
                  <div className="h-16 w-16 bg-primary/10 rounded-full flex items-center justify-center">
                    <MailCheck className="h-8 w-8 text-primary" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold">Check your email</h2>
                <p className="text-muted-foreground">
                  We've sent an activation link to <span className="font-medium text-foreground">{registeredEmail}</span>. 
                  Please click the link in the email to activate your account.
                </p>
                <div className="pt-4">
                  <Button 
                    variant="outline" 
                    className="w-full"
                    onClick={() => {
                      setRegisteredEmail(null);
                      const tabs = document.querySelector('[role="tablist"]');
                      const loginTab = tabs?.querySelector('[value="login"]') as HTMLButtonElement;
                      loginTab?.click();
                    }}
                  >
                    Back to Sign In
                  </Button>
                </div>
              </div>
            ) : (
              <>

            <TabsContent value="login">
              <div className="space-y-6">
                <div className="space-y-2 text-center">
                  <h2 className="text-2xl font-bold">Welcome back</h2>
                  <p className="text-muted-foreground">
                    Enter your credentials to access your account
                  </p>
                </div>

                <form onSubmit={handleLogin} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="email@example.com"
                      className="input-focus"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
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

                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 text-sm">
                      <input type="checkbox" className="rounded border-input" />
                      Remember me
                    </label>
                    <Link
                      to="/forgot-password"
                      className="text-sm text-primary hover:underline"
                    >
                      Forgot password?
                    </Link>
                  </div>

                  <Button
                    type="submit"
                    className="w-full"
                    size="lg"
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : null}
                    Sign In
                  </Button>
                </form>

              </div>
            </TabsContent>

            <TabsContent value="register">
              <div className="space-y-6">
                <div className="space-y-2 text-center">
                  <h2 className="text-2xl font-bold">Create an account</h2>
                  <p className="text-muted-foreground">
                    Register with your email
                  </p>
                </div>

                <form onSubmit={handleRegister} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="firstName">First Name</Label>
                      <Input
                        id="firstName"
                        placeholder="John"
                        className="input-focus"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="lastName">Last Name</Label>
                      <Input
                        id="lastName"
                        placeholder="Doe"
                        className="input-focus"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="studentId">Student ID</Label>
                    <Input
                      id="studentId"
                      placeholder="STU123456"
                      className="input-focus"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="regEmail">Email</Label>
                    <Input
                      id="regEmail"
                      type="email"
                      placeholder="student@university.edu"
                      className="input-focus"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="regPassword">Password</Label>
                    <div className="relative">
                      <Input
                        id="regPassword"
                        type={showRegPassword ? "text" : "password"}
                        placeholder="••••••••"
                        className="pr-10 input-focus"
                      />
                      <button
                        type="button"
                        onClick={() => setShowRegPassword(!showRegPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      >
                        {showRegPassword ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword">Confirm Password</Label>
                    <div className="relative">
                      <Input
                        id="confirmPassword"
                        type={showRegConfirmPassword ? "text" : "password"}
                        placeholder="••••••••"
                        className="pr-10 input-focus"
                      />
                      <button
                        type="button"
                        onClick={() =>
                          setShowRegConfirmPassword(!showRegConfirmPassword)
                        }
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      >
                        {showRegConfirmPassword ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </div>

                  <Button
                    type="submit"
                    className="w-full"
                    size="lg"
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : null}
                    Create Account
                  </Button>
                </form>

                <p className="text-center text-sm text-muted-foreground">
                  By registering, you agree to our{" "}
                  <Link to="/terms" className="text-primary hover:underline">
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link to="/privacy" className="text-primary hover:underline">
                    Privacy Policy
                  </Link>
                </p>
              </div>
            </TabsContent>
              </>
            )}
          </Tabs>
        </div>
      </div>
    </div>
  );
}
