/**
 * 注册页面 - 现代化设计
 */
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_BASE } from '../config/api';
import { Mail, User, Eye, EyeOff, AlertCircle, ArrowRight, Sparkles, Check, X, Shield } from 'lucide-react';

const RegisterPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [focusedField, setFocusedField] = useState<string | null>(null);

  const { register } = useAuth();
  const navigate = useNavigate();

  // 密码强度检查
  const passwordChecks = {
    length: password.length >= 8,
    upper: /[A-Z]/.test(password),
    lower: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
  };
  const passwordStrength = Object.values(passwordChecks).filter(Boolean).length;
  const passwordsMatch = password === confirmPassword;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!passwordsMatch) {
      setError('Passwords do not match');
      return;
    }

    if (passwordStrength < 3) {
      setError('Password is too weak');
      return;
    }

    setIsLoading(true);

    try {
      await register(email, password, displayName || undefined);
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOAuthLogin = (provider: string) => {
    window.location.href = `${API_BASE}/auth/oauth/${provider}`;
  };

  return (
    <div className="min-h-screen flex bg-surface">
      {/* Left Panel - Branding */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
        {/* Gradient Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-stone-900 via-stone-800 to-stone-900" />

        {/* Animated Orbs */}
        <div className="absolute top-20 right-20 w-72 h-72 bg-amber-400/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-20 left-20 w-96 h-96 bg-yellow-400/15 rounded-full blur-3xl animate-pulse delay-1000" />
        <div className="absolute top-1/2 right-1/3 w-64 h-64 bg-amber-300/10 rounded-full blur-3xl animate-pulse delay-500" />

        {/* Grid Pattern Overlay */}
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                             linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
            backgroundSize: '50px 50px',
          }}
        />

        {/* Content */}
        <div className="relative z-10 flex flex-col justify-center px-16 text-white">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
              <Sparkles className="w-7 h-7" />
            </div>
            <span className="text-2xl font-bold">Stock Agents</span>
          </div>

          <h1 className="text-5xl font-bold leading-tight mb-6">
            Start Your
            <br />
            Investment Journey
          </h1>

          <p className="text-xl text-white/80 mb-8 max-w-md">
            Join thousands of investors using AI-powered analysis to make smarter trading decisions.
          </p>

          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
                <Check className="w-4 h-4" />
              </div>
              <span className="text-white/90">Real-time multi-agent analysis</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
                <Check className="w-4 h-4" />
              </div>
              <span className="text-white/90">Bull vs Bear adversarial debates</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
                <Check className="w-4 h-4" />
              </div>
              <span className="text-white/90">A-shares, HK stocks & US markets</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel - Registration Form */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 overflow-y-auto">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden text-center mb-8">
            <div className="inline-flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-yellow-600 flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <span className="text-2xl font-bold text-white">Stock Agents</span>
            </div>
            <p className="text-stone-400">Start Your Investment Journey</p>
          </div>

          {/* Form Card */}
          <div className="bg-surface-raised/50 backdrop-blur-xl rounded-2xl p-8 border border-border/50 shadow-2xl">
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-white mb-2">Create account</h2>
              <p className="text-stone-400">Enter your details to get started</p>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 text-red-400">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span className="text-sm">{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Email Field */}
              <div className="relative">
                <label
                  className={`absolute left-4 transition-all duration-200 pointer-events-none ${
                    focusedField === 'email' || email
                      ? 'top-2 text-xs text-accent'
                      : 'top-1/2 -translate-y-1/2 text-stone-500'
                  }`}
                >
                  Email address
                </label>
                <Mail
                  className={`absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 transition-colors ${
                    focusedField === 'email' ? 'text-accent' : 'text-stone-600'
                  }`}
                />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onFocus={() => setFocusedField('email')}
                  onBlur={() => setFocusedField(null)}
                  className="w-full pt-6 pb-2 px-4 bg-surface-overlay/50 border border-border-strong/50 rounded-xl text-white focus:outline-none focus:border-accent/50 focus:ring-2 focus:ring-accent/20 transition-all"
                  required
                />
              </div>

              {/* Display Name Field */}
              <div className="relative">
                <label
                  className={`absolute left-4 transition-all duration-200 pointer-events-none ${
                    focusedField === 'displayName' || displayName
                      ? 'top-2 text-xs text-accent'
                      : 'top-1/2 -translate-y-1/2 text-stone-500'
                  }`}
                >
                  Display name (optional)
                </label>
                <User
                  className={`absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 transition-colors ${
                    focusedField === 'displayName' ? 'text-accent' : 'text-stone-600'
                  }`}
                />
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  onFocus={() => setFocusedField('displayName')}
                  onBlur={() => setFocusedField(null)}
                  className="w-full pt-6 pb-2 px-4 bg-surface-overlay/50 border border-border-strong/50 rounded-xl text-white focus:outline-none focus:border-accent/50 focus:ring-2 focus:ring-accent/20 transition-all"
                />
              </div>

              {/* Password Field */}
              <div className="relative">
                <label
                  className={`absolute left-4 transition-all duration-200 pointer-events-none ${
                    focusedField === 'password' || password
                      ? 'top-2 text-xs text-accent'
                      : 'top-1/2 -translate-y-1/2 text-stone-500'
                  }`}
                >
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-stone-500 hover:text-stone-300 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onFocus={() => setFocusedField('password')}
                  onBlur={() => setFocusedField(null)}
                  className="w-full pt-6 pb-2 px-4 pr-12 bg-surface-overlay/50 border border-border-strong/50 rounded-xl text-white focus:outline-none focus:border-accent/50 focus:ring-2 focus:ring-accent/20 transition-all"
                  required
                />
              </div>

              {/* Password Strength Indicator */}
              {password && (
                <div className="space-y-3 p-4 bg-surface-overlay/30 rounded-xl border border-border-strong/30">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-stone-400" />
                    <span className="text-xs text-stone-400 font-medium">Password Strength</span>
                  </div>

                  {/* Strength Bar */}
                  <div className="flex gap-1.5">
                    {[1, 2, 3, 4].map((level) => (
                      <div
                        key={level}
                        className={`h-1.5 flex-1 rounded-full transition-colors ${
                          passwordStrength >= level
                            ? passwordStrength >= 4
                              ? 'bg-green-500'
                              : passwordStrength >= 3
                                ? 'bg-blue-500'
                                : passwordStrength >= 2
                                  ? 'bg-yellow-500'
                                  : 'bg-red-500'
                            : 'bg-surface-muted'
                        }`}
                      />
                    ))}
                  </div>

                  {/* Check Items */}
                  <div className="grid grid-cols-2 gap-2">
                    <div className={`flex items-center gap-2 text-xs ${passwordChecks.length ? 'text-green-400' : 'text-stone-500'}`}>
                      {passwordChecks.length ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                      8+ characters
                    </div>
                    <div className={`flex items-center gap-2 text-xs ${passwordChecks.upper ? 'text-green-400' : 'text-stone-500'}`}>
                      {passwordChecks.upper ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                      Uppercase
                    </div>
                    <div className={`flex items-center gap-2 text-xs ${passwordChecks.lower ? 'text-green-400' : 'text-stone-500'}`}>
                      {passwordChecks.lower ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                      Lowercase
                    </div>
                    <div className={`flex items-center gap-2 text-xs ${passwordChecks.number ? 'text-green-400' : 'text-stone-500'}`}>
                      {passwordChecks.number ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                      Number
                    </div>
                  </div>
                </div>
              )}

              {/* Confirm Password Field */}
              <div className="relative">
                <label
                  className={`absolute left-4 transition-all duration-200 pointer-events-none ${
                    focusedField === 'confirmPassword' || confirmPassword
                      ? 'top-2 text-xs text-accent'
                      : 'top-1/2 -translate-y-1/2 text-stone-500'
                  }`}
                >
                  Confirm password
                </label>
                {confirmPassword && (
                  <div className="absolute right-4 top-1/2 -translate-y-1/2">
                    {passwordsMatch ? (
                      <Check className="w-5 h-5 text-green-400" />
                    ) : (
                      <X className="w-5 h-5 text-red-400" />
                    )}
                  </div>
                )}
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  onFocus={() => setFocusedField('confirmPassword')}
                  onBlur={() => setFocusedField(null)}
                  className={`w-full pt-6 pb-2 px-4 pr-12 bg-surface-overlay/50 border rounded-xl text-white focus:outline-none focus:ring-2 transition-all ${
                    confirmPassword && !passwordsMatch
                      ? 'border-red-500/50 focus:border-red-500/50 focus:ring-red-500/20'
                      : 'border-border-strong/50 focus:border-accent/50 focus:ring-accent/20'
                  }`}
                  required
                />
              </div>
              {confirmPassword && !passwordsMatch && (
                <p className="text-xs text-red-400 -mt-3 ml-1">Passwords do not match</p>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading || passwordStrength < 3 || !passwordsMatch}
                className="w-full py-3.5 bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-500 hover:to-yellow-500 disabled:from-stone-600 disabled:to-stone-600 text-white font-semibold rounded-xl transition-all duration-200 flex items-center justify-center gap-2 group shadow-lg shadow-glow-gold hover:shadow-glow-gold disabled:shadow-none"
              >
                {isLoading ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    Create Account
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </>
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="relative my-8">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border-strong/50" />
              </div>
              <div className="relative flex justify-center">
                <span className="px-4 bg-surface-raised/50 text-stone-500 text-sm">or continue with</span>
              </div>
            </div>

            {/* OAuth Buttons */}
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => handleOAuthLogin('google')}
                className="flex items-center justify-center gap-3 py-3 px-4 bg-surface-overlay/50 hover:bg-surface-muted/50 border border-border-strong/50 rounded-xl text-white transition-all duration-200 group"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                <span className="text-sm font-medium">Google</span>
              </button>

              <button
                onClick={() => handleOAuthLogin('github')}
                className="flex items-center justify-center gap-3 py-3 px-4 bg-surface-overlay/50 hover:bg-surface-muted/50 border border-border-strong/50 rounded-xl text-white transition-all duration-200 group"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                </svg>
                <span className="text-sm font-medium">GitHub</span>
              </button>
            </div>

            {/* Sign In Link */}
            <p className="mt-8 text-center text-stone-400">
              Already have an account?{' '}
              <Link to="/login" className="text-accent hover:text-accent-hover font-medium transition-colors">
                Sign in
              </Link>
            </p>
          </div>

          {/* Footer */}
          <p className="mt-8 text-center text-stone-600 text-sm">
            By creating an account, you agree to our{' '}
            <a href="#" className="text-stone-500 hover:text-stone-400">Terms of Service</a>
            {' '}and{' '}
            <a href="#" className="text-stone-500 hover:text-stone-400">Privacy Policy</a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
