import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, Lock, Mail, User } from "lucide-react";

export default function Login() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isLogin) {
        const { data } = await api.post("/auth/login", { email, password });
        localStorage.setItem("token", data.access_token);
        navigate("/");
      } else {
        const { data } = await api.post("/auth/signup", { email, full_name: name, password });
        localStorage.setItem("token", data.access_token);
        navigate("/");
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center mb-4 text-primary">
            <TrendingUp size={28} />
          </div>
          <h1 className="text-3xl font-bold tracking-tight">RetailSense</h1>
          <p className="text-muted-foreground mt-2 text-center">
            AI-powered retail analytics & demand forecasting platform
          </p>
        </div>

        <Card className="border-border/50 shadow-2xl bg-card/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle>{isLogin ? "Welcome back" : "Create an account"}</CardTitle>
            <CardDescription>
              {isLogin
                ? "Enter your credentials to access your dashboard"
                : "Enter your details to start analyzing your data"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {!isLogin && (
                <div className="space-y-2">
                  <div className="relative">
                    <User className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Full Name"
                      className="pl-9"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                    />
                  </div>
                </div>
              )}
              <div className="space-y-2">
                <div className="relative">
                  <Mail className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="email"
                    placeholder="Email address"
                    className="pl-9"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="space-y-2">
                <div className="relative">
                  <Lock className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="password"
                    placeholder="Password"
                    className="pl-9"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>
              </div>

              {error && <div className="p-3 text-sm bg-destructive/10 text-destructive rounded-md border border-destructive/20">{error}</div>}

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Please wait..." : isLogin ? "Sign In" : "Sign Up"}
              </Button>
            </form>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <div className="text-sm text-center text-muted-foreground">
              {isLogin ? "Don't have an account? " : "Already have an account? "}
              <button
                type="button"
                onClick={() => setIsLogin(!isLogin)}
                className="text-primary hover:underline font-medium"
              >
                {isLogin ? "Sign up" : "Sign in"}
              </button>
            </div>
            
            {isLogin && (
              <div className="p-4 rounded-lg bg-muted/50 border border-border/50 text-xs text-center w-full">
                <p className="font-semibold text-foreground mb-1">Demo Account</p>
                <p>Email: <span className="font-mono bg-background px-1 rounded">demo@retailsense.io</span></p>
                <p>Pass: <span className="font-mono bg-background px-1 rounded">Demo@RetailSense2024</span></p>
              </div>
            )}
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
