/**
 * Profile & Settings Page
 * User profile information and security settings
 */

import { useState, FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { authService } from '@/services/api/authService';
import { PasswordStrengthMeter } from '@/components/auth/PasswordStrengthMeter';
import {
  KeyIcon,
  DevicePhoneMobileIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  EyeIcon,
  EyeSlashIcon,
} from '@heroicons/react/24/outline';

export function ProfilePage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'profile' | 'security' | 'sessions'>('profile');

  // Password change state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const handlePasswordChange = async (e: FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(false);

    // Validation
    if (newPassword.length < 8) {
      setPasswordError('New password must be at least 8 characters');
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match');
      return;
    }

    setIsChangingPassword(true);

    try {
      await authService.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });

      setPasswordSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');

      // Clear success message after 5 seconds
      setTimeout(() => setPasswordSuccess(false), 5000);
    } catch (err: any) {
      setPasswordError(err.response?.data?.detail || 'Failed to change password');
    } finally {
      setIsChangingPassword(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-fadeIn">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-heading font-bold text-saturn-900">Profile & Settings</h1>
        <p className="text-saturn-600 mt-2">
          Manage your account information and security settings
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-saturn-200">
        <div className="flex gap-1">
          <button
            onClick={() => setActiveTab('profile')}
            className={`px-4 py-3 font-medium text-sm transition-colors ${
              activeTab === 'profile'
                ? 'text-saturn-900 border-b-2 border-saturn-600'
                : 'text-saturn-600 hover:text-saturn-900'
            }`}
          >
            Profile
          </button>
          <button
            onClick={() => setActiveTab('security')}
            className={`px-4 py-3 font-medium text-sm transition-colors ${
              activeTab === 'security'
                ? 'text-saturn-900 border-b-2 border-saturn-600'
                : 'text-saturn-600 hover:text-saturn-900'
            }`}
          >
            Security
          </button>
          <button
            onClick={() => setActiveTab('sessions')}
            className={`px-4 py-3 font-medium text-sm transition-colors ${
              activeTab === 'sessions'
                ? 'text-saturn-900 border-b-2 border-saturn-600'
                : 'text-saturn-600 hover:text-saturn-900'
            }`}
          >
            Active Sessions
          </button>
        </div>
      </div>

      {/* Profile Tab */}
      {activeTab === 'profile' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* User avatar */}
          <div className="glass-neo border border-saturn-200/50 rounded-2xl p-6 text-center">
            <div className="inline-flex items-center justify-center w-24 h-24 rounded-2xl bg-gradient-to-br from-sun-400 via-saturn-500 to-mars-500 shadow-xl shadow-saturn-500/30 mb-4">
              <span className="text-white font-heading font-bold text-3xl">
                {user?.full_name?.substring(0, 2).toUpperCase() || 'U'}
              </span>
            </div>
            <h3 className="font-heading font-bold text-saturn-900 text-lg">{user?.full_name}</h3>
            <p className="text-sm text-saturn-600 mt-1">{user?.role || user?.user_type}</p>
          </div>

          {/* User details */}
          <div className="md:col-span-2 glass-neo border border-saturn-200/50 rounded-2xl p-6 space-y-4">
            <h3 className="font-heading font-bold text-saturn-900 text-lg mb-4">Account Information</h3>
            
            <div>
              <label className="block text-sm font-medium text-saturn-700 mb-1">Full Name</label>
              <p className="text-saturn-900">{user?.full_name || '-'}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-saturn-700 mb-1">Email</label>
              <p className="text-saturn-900">{user?.email || '-'}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-saturn-700 mb-1">User Type</label>
              <p className="text-saturn-900">{user?.user_type || '-'}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-saturn-700 mb-1">User ID</label>
              <p className="text-saturn-500 font-mono text-sm">{user?.id || '-'}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-saturn-700 mb-1">Account Status</label>
              <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${
                user?.is_active 
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-mars-100 text-mars-700'
              }`}>
                {user?.is_active ? (
                  <>
                    <CheckCircleIcon className="w-4 h-4" />
                    Active
                  </>
                ) : (
                  <>
                    <ExclamationCircleIcon className="w-4 h-4" />
                    Inactive
                  </>
                )}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Security Tab */}
      {activeTab === 'security' && (
        <div className="glass-neo border border-saturn-200/50 rounded-2xl p-6">
          <h3 className="font-heading font-bold text-saturn-900 text-lg mb-6 flex items-center gap-2">
            <KeyIcon className="w-6 h-6" />
            Change Password
          </h3>

          {/* Success message */}
          {passwordSuccess && (
            <div className="mb-6 p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-start gap-3 animate-fadeIn">
              <CheckCircleIcon className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm font-medium text-emerald-900">Password changed successfully!</p>
            </div>
          )}

          {/* Error message */}
          {passwordError && (
            <div className="mb-6 p-4 bg-mars-50 border border-mars-200 rounded-xl flex items-start gap-3 animate-fadeIn">
              <ExclamationCircleIcon className="w-5 h-5 text-mars-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm font-medium text-mars-900">{passwordError}</p>
            </div>
          )}

          <form onSubmit={handlePasswordChange} className="max-w-md space-y-5">
            {/* Current password */}
            <div>
              <label htmlFor="current-password" className="block text-sm font-medium text-saturn-900 mb-2">
                Current Password
              </label>
              <div className="relative">
                <input
                  id="current-password"
                  type={showCurrentPassword ? 'text' : 'password'}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  required
                  className="block w-full px-4 py-3 pr-12 border border-saturn-200 rounded-xl bg-white/50 text-saturn-900 placeholder-saturn-400 focus:outline-none focus:ring-2 focus:ring-saturn-500 focus:border-transparent transition-all"
                  placeholder="Enter current password"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  tabIndex={-1}
                >
                  {showCurrentPassword ? (
                    <EyeSlashIcon className="h-5 w-5 text-saturn-400 hover:text-saturn-600" />
                  ) : (
                    <EyeIcon className="h-5 w-5 text-saturn-400 hover:text-saturn-600" />
                  )}
                </button>
              </div>
            </div>

            {/* New password */}
            <div>
              <label htmlFor="new-password" className="block text-sm font-medium text-saturn-900 mb-2">
                New Password
              </label>
              <div className="relative">
                <input
                  id="new-password"
                  type={showNewPassword ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                  className="block w-full px-4 py-3 pr-12 border border-saturn-200 rounded-xl bg-white/50 text-saturn-900 placeholder-saturn-400 focus:outline-none focus:ring-2 focus:ring-saturn-500 focus:border-transparent transition-all"
                  placeholder="Enter new password"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  tabIndex={-1}
                >
                  {showNewPassword ? (
                    <EyeSlashIcon className="h-5 w-5 text-saturn-400 hover:text-saturn-600" />
                  ) : (
                    <EyeIcon className="h-5 w-5 text-saturn-400 hover:text-saturn-600" />
                  )}
                </button>
              </div>
              
              {/* Password strength meter */}
              {newPassword && (
                <div className="mt-3">
                  <PasswordStrengthMeter password={newPassword} />
                </div>
              )}
            </div>

            {/* Confirm password */}
            <div>
              <label htmlFor="confirm-password" className="block text-sm font-medium text-saturn-900 mb-2">
                Confirm New Password
              </label>
              <input
                id="confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                className="block w-full px-4 py-3 border border-saturn-200 rounded-xl bg-white/50 text-saturn-900 placeholder-saturn-400 focus:outline-none focus:ring-2 focus:ring-saturn-500 focus:border-transparent transition-all"
                placeholder="Confirm new password"
              />
            </div>

            <button
              type="submit"
              disabled={isChangingPassword}
              className="w-full py-3 px-4 bg-gradient-to-r from-saturn-600 to-saturn-700 hover:from-saturn-700 hover:to-saturn-800 text-white font-heading font-semibold rounded-xl shadow-lg shadow-saturn-500/30 hover:shadow-xl hover:shadow-saturn-500/40 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-saturn-500 transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
            >
              {isChangingPassword ? 'Changing Password...' : 'Change Password'}
            </button>
          </form>
        </div>
      )}

      {/* Sessions Tab */}
      {activeTab === 'sessions' && (
        <div className="glass-neo border border-saturn-200/50 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-heading font-bold text-saturn-900 text-lg flex items-center gap-2">
              <DevicePhoneMobileIcon className="w-6 h-6" />
              Active Sessions
            </h3>
            <Link
              to="/backoffice/settings/sessions"
              className="text-sm font-medium text-saturn-600 hover:text-saturn-900 transition-colors"
            >
              View All Sessions →
            </Link>
          </div>
          <p className="text-saturn-600 mb-4">
            Manage your active login sessions across all devices from the sessions page.
          </p>
          
          <Link
            to="/backoffice/settings/2fa"
            className="inline-flex items-center gap-2 text-sm font-medium text-saturn-600 hover:text-saturn-900 transition-colors"
          >
            <KeyIcon className="w-4 h-4" />
            Configure Two-Factor Authentication →
          </Link>
        </div>
      )}
    </div>
  );
}
