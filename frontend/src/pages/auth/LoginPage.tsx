/**
 * Login Page - Internal Backoffice Auth
 * Email/Password authentication for internal users
 */

import { useState, FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { 
  EnvelopeIcon, 
  LockClosedIcon,
  ExclamationCircleIcon,
  EyeIcon,
  EyeSlashIcon,
} from '@heroicons/react/24/outline';

export function LoginPage() {
  const navigate = useNavigate();
  const { login, isLoading, error, clearError } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    clearError();

    try {
      await login({ email, password });
      navigate('/backoffice');
    } catch (error) {
      // Error is already set in store
      console.error('Login failed:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-pearl-50 via-saturn-50/30 to-sun-50/20 flex items-center justify-center p-4 font-body">
      {/* Background decoration */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-sun-200/20 to-transparent rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-gradient-to-tr from-saturn-200/20 to-transparent rounded-full blur-3xl" />
      </div>

      {/* Login card */}
      <div className="relative w-full max-w-md">
        {/* Logo and header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-sun-400 via-saturn-500 to-mars-500 shadow-xl shadow-saturn-500/30 mb-4">
            <span className="text-white font-heading font-bold text-2xl">RN</span>
          </div>
          <h1 className="text-3xl font-heading font-bold text-saturn-900 mb-2">
            RNRL Backoffice
          </h1>
          <p className="text-saturn-600 font-medium">
            Sign in to your account
          </p>
        </div>

        {/* Login form */}
        <div className="glass-neo border border-saturn-200/50 rounded-2xl shadow-2xl shadow-saturn-500/10 p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Error message */}
            {error && (
              <div className="p-4 bg-mars-50 border border-mars-200 rounded-xl flex items-start gap-3 animate-fadeIn">
                <ExclamationCircleIcon className="w-5 h-5 text-mars-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-mars-900">{error}</p>
                </div>
              </div>
            )}

            {/* Email field */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-saturn-900 mb-2">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <EnvelopeIcon className="h-5 w-5 text-saturn-400" />
                </div>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  className="block w-full pl-10 pr-3 py-3 border border-saturn-200 rounded-xl bg-white/50 text-saturn-900 placeholder-saturn-400 focus:outline-none focus:ring-2 focus:ring-saturn-500 focus:border-transparent transition-all duration-150"
                  placeholder="your@email.com"
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* Password field */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-saturn-900 mb-2">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <LockClosedIcon className="h-5 w-5 text-saturn-400" />
                </div>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  className="block w-full pl-10 pr-12 py-3 border border-saturn-200 rounded-xl bg-white/50 text-saturn-900 placeholder-saturn-400 focus:outline-none focus:ring-2 focus:ring-saturn-500 focus:border-transparent transition-all duration-150"
                  placeholder="••••••••"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <EyeSlashIcon className="h-5 w-5 text-saturn-400 hover:text-saturn-600 transition-colors" />
                  ) : (
                    <EyeIcon className="h-5 w-5 text-saturn-400 hover:text-saturn-600 transition-colors" />
                  )}
                </button>
              </div>
            </div>

            {/* Remember me & Forgot password */}
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  id="remember-me"
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="h-4 w-4 text-saturn-600 focus:ring-saturn-500 border-saturn-300 rounded"
                />
                <label htmlFor="remember-me" className="ml-2 block text-sm text-saturn-700">
                  Remember me
                </label>
              </div>

              <Link
                to="/forgot-password"
                className="text-sm font-medium text-saturn-600 hover:text-saturn-900 transition-colors"
              >
                Forgot password?
              </Link>
            </div>

            {/* Submit button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 bg-gradient-to-r from-saturn-600 to-saturn-700 hover:from-saturn-700 hover:to-saturn-800 text-white font-heading font-semibold rounded-xl shadow-lg shadow-saturn-500/30 hover:shadow-xl hover:shadow-saturn-500/40 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-saturn-500 transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Signing in...
                </span>
              ) : (
                'Sign in'
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="mt-6 pt-6 border-t border-saturn-200/40">
            <p className="text-center text-xs text-saturn-500">
              RNRL Cotton ERP • 2040 Vision • Secure Access
            </p>
          </div>
        </div>

        {/* System info */}
        <div className="mt-6 text-center">
          <p className="text-xs text-saturn-400 font-mono">
            Environment: {import.meta.env.MODE} | v2.0.40
          </p>
        </div>
      </div>
    </div>
  );
}
