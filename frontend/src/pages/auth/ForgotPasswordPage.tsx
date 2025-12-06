/**
 * Forgot Password Page
 * Request password reset link
 */

import { useState, FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { authService } from '@/services/api/authService';
import {
  EnvelopeIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ArrowLeftIcon,
} from '@heroicons/react/24/outline';

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await authService.forgotPassword(email);
      setSuccess(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send reset email. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-space-900 via-saturn-900 to-sun-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full glass-neo border-2 border-emerald-400/50 rounded-2xl p-8 shadow-2xl shadow-emerald-500/20 animate-scaleIn">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-500/30">
              <CheckCircleIcon className="w-10 h-10 text-white" />
            </div>
          </div>

          <h2 className="text-2xl font-heading font-bold text-space-900 text-center mb-3">
            Check Your Email
          </h2>

          <p className="text-saturn-700 text-center mb-6">
            We've sent password reset instructions to <strong>{email}</strong>
          </p>

          <div className="bg-gradient-to-br from-sun-50 to-saturn-50 border border-sun-200 rounded-xl p-4 mb-6">
            <p className="text-xs text-saturn-700">
              <strong>Note:</strong> The reset link will expire in 1 hour. If you don't see the email, check your spam folder.
            </p>
          </div>

          <Link
            to="/login"
            className="block w-full py-3 px-4 bg-gradient-to-r from-saturn-600 to-saturn-700 hover:from-saturn-700 hover:to-saturn-800 text-white text-center font-heading font-semibold rounded-xl shadow-lg shadow-saturn-500/30 hover:shadow-xl hover:shadow-saturn-500/40 transition-all duration-150 active:scale-[0.98]"
          >
            Back to Login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-space-900 via-saturn-900 to-sun-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Logo */}
        <div className="text-center mb-8 animate-fadeIn">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-sun-400 via-saturn-500 to-mars-500 shadow-2xl shadow-saturn-500/40 mb-4">
            <span className="text-white font-heading font-bold text-3xl">RN</span>
          </div>
          <h1 className="text-4xl font-heading font-bold text-pearl-50 mb-2">
            Reset Password
          </h1>
          <p className="text-pearl-300">
            Enter your email to receive reset instructions
          </p>
        </div>

        {/* Form */}
        <div className="glass-neo border border-pearl-200/30 rounded-2xl p-8 shadow-2xl shadow-saturn-900/50 animate-scaleIn">
          {error && (
            <div className="mb-6 p-4 bg-mars-50 border border-mars-200 rounded-xl flex items-start gap-3 animate-fadeIn">
              <ExclamationCircleIcon className="w-5 h-5 text-mars-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm font-medium text-mars-900">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-pearl-100 mb-2">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <EnvelopeIcon className="h-5 w-5 text-pearl-400" />
                </div>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="block w-full pl-10 pr-4 py-3 border border-pearl-200/30 rounded-xl bg-pearl-50/10 text-pearl-50 placeholder-pearl-400 focus:outline-none focus:ring-2 focus:ring-saturn-500 focus:border-transparent transition-all"
                  placeholder="your@email.com"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 bg-gradient-to-r from-saturn-600 to-saturn-700 hover:from-saturn-700 hover:to-saturn-800 text-white font-heading font-semibold rounded-xl shadow-lg shadow-saturn-500/30 hover:shadow-xl hover:shadow-saturn-500/40 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-saturn-500 transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
            >
              {isLoading ? 'Sending...' : 'Send Reset Link'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <Link
              to="/login"
              className="inline-flex items-center gap-2 text-sm font-medium text-pearl-300 hover:text-pearl-100 transition-colors"
            >
              <ArrowLeftIcon className="w-4 h-4" />
              Back to Login
            </Link>
          </div>
        </div>

        {/* Environment indicator */}
        {import.meta.env.MODE === 'development' && (
          <div className="mt-4 text-center">
            <span className="text-xs text-pearl-400">Development Mode</span>
          </div>
        )}
      </div>
    </div>
  );
}
