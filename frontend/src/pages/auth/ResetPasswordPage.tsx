/**
 * Reset Password Page
 * Reset password with token from email
 */

import { useState, FormEvent, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { authService } from '@/services/api/authService';
import { PasswordStrengthMeter } from '@/components/auth/PasswordStrengthMeter';
import {
  KeyIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  EyeIcon,
  EyeSlashIcon,
} from '@heroicons/react/24/outline';

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const tokenFromUrl = searchParams.get('token');
    if (tokenFromUrl) {
      setToken(tokenFromUrl);
    } else {
      setError('Invalid reset link. Please request a new password reset.');
    }
  }, [searchParams]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    if (!token) {
      setError('Invalid reset token');
      return;
    }

    setIsLoading(true);

    try {
      await authService.resetPassword(token, newPassword);
      setSuccess(true);
      
      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reset password. The link may have expired.');
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
            Password Reset Successful
          </h2>

          <p className="text-saturn-700 text-center mb-6">
            Your password has been updated successfully. Redirecting to login...
          </p>

          <Link
            to="/login"
            className="block w-full py-3 px-4 bg-gradient-to-r from-saturn-600 to-saturn-700 hover:from-saturn-700 hover:to-saturn-800 text-white text-center font-heading font-semibold rounded-xl shadow-lg shadow-saturn-500/30 hover:shadow-xl hover:shadow-saturn-500/40 transition-all duration-150 active:scale-[0.98]"
          >
            Go to Login
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
            Create New Password
          </h1>
          <p className="text-pearl-300">
            Enter your new password below
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
              <label htmlFor="new-password" className="block text-sm font-medium text-pearl-100 mb-2">
                New Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <KeyIcon className="h-5 w-5 text-pearl-400" />
                </div>
                <input
                  id="new-password"
                  type={showPassword ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                  className="block w-full pl-10 pr-12 py-3 border border-pearl-200/30 rounded-xl bg-pearl-50/10 text-pearl-50 placeholder-pearl-400 focus:outline-none focus:ring-2 focus:ring-saturn-500 focus:border-transparent transition-all"
                  placeholder="Enter new password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <EyeSlashIcon className="h-5 w-5 text-pearl-400 hover:text-pearl-200" />
                  ) : (
                    <EyeIcon className="h-5 w-5 text-pearl-400 hover:text-pearl-200" />
                  )}
                </button>
              </div>

              {newPassword && (
                <div className="mt-3">
                  <PasswordStrengthMeter password={newPassword} />
                </div>
              )}
            </div>

            <div>
              <label htmlFor="confirm-password" className="block text-sm font-medium text-pearl-100 mb-2">
                Confirm Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <KeyIcon className="h-5 w-5 text-pearl-400" />
                </div>
                <input
                  id="confirm-password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  className="block w-full pl-10 pr-4 py-3 border border-pearl-200/30 rounded-xl bg-pearl-50/10 text-pearl-50 placeholder-pearl-400 focus:outline-none focus:ring-2 focus:ring-saturn-500 focus:border-transparent transition-all"
                  placeholder="Confirm new password"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading || !token}
              className="w-full py-3 px-4 bg-gradient-to-r from-saturn-600 to-saturn-700 hover:from-saturn-700 hover:to-saturn-800 text-white font-heading font-semibold rounded-xl shadow-lg shadow-saturn-500/30 hover:shadow-xl hover:shadow-saturn-500/40 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-saturn-500 transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
            >
              {isLoading ? 'Resetting...' : 'Reset Password'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <Link
              to="/login"
              className="text-sm font-medium text-pearl-300 hover:text-pearl-100 transition-colors"
            >
              Back to Login
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
