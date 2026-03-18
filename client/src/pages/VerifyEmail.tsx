import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { GraduationCap, CheckCircle2, XCircle, Loader2, ArrowRight } from "lucide-react";
import { Button } from "../components/ui/button";
import { useToast } from "../hooks/use-toast";
import { API_BASE_URL } from "../lib/api";

export default function VerifyEmail() {
  const { token } = useParams<{ token: string }>();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");
  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    const verifyToken = async () => {
      if (!token) {
        setStatus("error");
        setMessage("Invalid verification link.");
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/auth/verify-email/${token}/`, {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
          },
        });

        const data = await response.json();

        if (response.ok) {
          setStatus("success");
          setMessage(data.message || "Your account has been successfully verified!");
          toast({
            title: "Verification Successful",
            description: "You can now sign in to your account.",
          });
        } else {
          setStatus("error");
          setMessage(data.error || "Verification failed. The link may be expired or invalid.");
        }
      } catch (error) {
        setStatus("error");
        setMessage("Network error. Please check your connection and try again.");
      }
    };

    verifyToken();
  }, [token, toast]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8 gradient-hero">
      <div className="w-full max-w-md bg-background rounded-2xl shadow-xl p-8 space-y-8 animate-in fade-in zoom-in duration-500">
        <div className="text-center space-y-2">
          <div className="flex justify-center mb-6">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary shadow-lg">
              <GraduationCap className="h-10 w-10 text-primary-foreground" />
            </div>
          </div>
          <h1 className="text-3xl font-bold">CampusFix</h1>
        </div>

        <div className="py-4">
          {status === "loading" && (
            <div className="text-center space-y-4">
              <div className="flex justify-center">
                <Loader2 className="h-12 w-12 text-primary animate-spin" />
              </div>
              <h2 className="text-xl font-semibold">Verifying your account...</h2>
              <p className="text-muted-foreground italic">Please wait while we confirm your email.</p>
            </div>
          )}

          {status === "success" && (
            <div className="text-center space-y-4 animate-in slide-in-from-bottom-4 duration-500">
              <div className="flex justify-center">
                <div className="h-20 w-20 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
                  <CheckCircle2 className="h-12 w-12 text-green-600 dark:text-green-400" />
                </div>
              </div>
              <h2 className="text-2xl font-bold text-green-600 dark:text-green-400">Success!</h2>
              <p className="text-lg leading-relaxed">{message}</p>
              <div className="pt-6">
                <Button className="w-full h-12 text-lg font-medium group" onClick={() => navigate("/login")}>
                  Continue to Sign In
                  <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" />
                </Button>
              </div>
            </div>
          )}

          {status === "error" && (
            <div className="text-center space-y-4 animate-in slide-in-from-bottom-4 duration-500">
              <div className="flex justify-center">
                <div className="h-20 w-20 bg-destructive/10 rounded-full flex items-center justify-center">
                  <XCircle className="h-12 w-12 text-destructive" />
                </div>
              </div>
              <h2 className="text-2xl font-bold text-destructive">Verification Failed</h2>
              <p className="text-lg leading-relaxed">{message}</p>
              <div className="pt-6">
                <Button variant="outline" className="w-full h-12 text-lg font-medium" onClick={() => navigate("/login")}>
                  Back to Registration
                </Button>
              </div>
            </div>
          )}
        </div>

        <div className="text-center">
          <p className="text-sm text-muted-foreground">
            Contact support if you're having issues:{" "}
            <a href="mailto:support@campusfix.edu" className="text-primary hover:underline font-medium">
              support@campusfix.edu
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
