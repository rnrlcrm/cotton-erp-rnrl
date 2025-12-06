/**
 * Two-Factor Authentication Setup Page
 * Enable/disable 2FA with QR code and verification
 */

import { useState, useEffect } from 'react';
import { authService } from '@/services/api/authService';
import {
  ShieldCheckIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';

export function TwoFactorPage() {
  const [isEnabled, setIsEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [secret, setSecret] = useState<string | null>(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [step, setStep] = useState<'status' | 'setup' | 'verify'>('status');

  // Check 2FA status on mount
  useEffect(() => {
    check2FAStatus();
  }, []);

  const check2FAStatus = async () => {
    try {
      // Assuming backend has endpoint GET /auth/2fa/status
      const response = await authService.get2FAStatus();
      setIsEnabled(response.enabled);
    } catch (err) {
      console.error('Failed to check 2FA status:', err);
    }
  };

  const handleEnable2FA = async () => {
    setError(null);
    setIsLoading(true);

    try {
      // Generate QR code - POST /auth/2fa/setup
      const response = await authService.setup2FA();
      setQrCode(response.qr_code);
      setSecret(response.secret);
      setStep('setup');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate 2FA setup');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyAndEnable = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      // Verify code and enable - POST /auth/2fa/verify
      await authService.verify2FA(verificationCode);
      setSuccess('Two-factor authentication enabled successfully!');
      setIsEnabled(true);
      setStep('status');
      setVerificationCode('');
      setQrCode(null);
      setSecret(null);
      
      setTimeout(() => setSuccess(null), 5000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid verification code');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisable2FA = async () => {
    if (!confirm('Are you sure you want to disable two-factor authentication? This will make your account less secure.')) {
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      // Disable 2FA - DELETE /auth/2fa
      await authService.disable2FA();
      setSuccess('Two-factor authentication disabled');
      setIsEnabled(false);
      
      setTimeout(() => setSuccess(null), 5000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to disable 2FA');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setStep('status');
    setQrCode(null);
    setSecret(null);
    setVerificationCode('');
    setError(null);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fadeIn">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-heading font-bold text-saturn-900">Two-Factor Authentication</h1>
        <p className="text-saturn-600 mt-2">
          Add an extra layer of security to your account
        </p>
      </div>

      {/* Success/Error messages */}
      {success && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-start gap-3 animate-fadeIn">
          <CheckCircleIcon className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm font-medium text-emerald-900">{success}</p>
        </div>
      )}

      {error && (
        <div className="p-4 bg-mars-50 border border-mars-200 rounded-xl flex items-start gap-3 animate-fadeIn">
          <ExclamationCircleIcon className="w-5 h-5 text-mars-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm font-medium text-mars-900">{error}</p>
        </div>
      )}

      {/* Status View */}
      {step === 'status' && (
        <div className="glass-neo border border-saturn-200/50 rounded-2xl p-6">
          <div className="flex items-start gap-4">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
              isEnabled 
                ? 'bg-gradient-to-br from-emerald-400 to-emerald-600 shadow-lg shadow-emerald-500/30'
                : 'bg-gradient-to-br from-saturn-400 to-saturn-600 shadow-lg shadow-saturn-500/30'
            }`}>
              <ShieldCheckIcon className="w-7 h-7 text-white" />
            </div>

            <div className="flex-1">
              <h3 className="font-heading font-bold text-saturn-900 text-lg mb-1">
                {isEnabled ? '2FA Enabled' : '2FA Not Enabled'}
              </h3>
              <p className="text-saturn-600 text-sm mb-4">
                {isEnabled
                  ? 'Your account is protected with two-factor authentication. You need your authenticator app to log in.'
                  : 'Add an extra layer of security by requiring a verification code from your mobile device in addition to your password.'}
              </p>

              {isEnabled ? (
                <button
                  onClick={handleDisable2FA}
                  disabled={isLoading}
                  className="py-2 px-4 bg-mars-100 hover:bg-mars-200 text-mars-700 font-heading font-semibold rounded-xl transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
                >
                  {isLoading ? 'Disabling...' : 'Disable 2FA'}
                </button>
              ) : (
                <button
                  onClick={handleEnable2FA}
                  disabled={isLoading}
                  className="py-2 px-4 bg-gradient-to-r from-saturn-600 to-saturn-700 hover:from-saturn-700 hover:to-saturn-800 text-white font-heading font-semibold rounded-xl shadow-lg shadow-saturn-500/30 hover:shadow-xl hover:shadow-saturn-500/40 transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
                >
                  {isLoading ? 'Setting up...' : 'Enable 2FA'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Setup View - Show QR Code */}
      {step === 'setup' && qrCode && (
        <div className="glass-neo border border-saturn-200/50 rounded-2xl p-6 space-y-6">
          <div className="text-center">
            <h3 className="font-heading font-bold text-saturn-900 text-xl mb-2">
              Scan QR Code
            </h3>
            <p className="text-saturn-600">
              Use an authenticator app like Google Authenticator or Authy to scan this QR code
            </p>
          </div>

          {/* QR Code */}
          <div className="flex justify-center">
            <div className="bg-white p-6 rounded-2xl border-2 border-saturn-200 shadow-lg">
              <img 
                src={qrCode} 
                alt="2FA QR Code" 
                className="w-64 h-64"
              />
            </div>
          </div>

          {/* Manual entry code */}
          {secret && (
            <div className="bg-saturn-50 border border-saturn-200 rounded-xl p-4">
              <p className="text-xs font-medium text-saturn-700 mb-2">
                Or enter this code manually:
              </p>
              <code className="block font-mono text-sm text-saturn-900 bg-white px-3 py-2 rounded-lg border border-saturn-200">
                {secret}
              </code>
            </div>
          )}

          {/* Next step button */}
          <div className="flex gap-3">
            <button
              onClick={handleCancel}
              className="flex-1 py-3 px-4 bg-saturn-100 hover:bg-saturn-200 text-saturn-700 font-heading font-semibold rounded-xl transition-all duration-150 active:scale-[0.98]"
            >
              Cancel
            </button>
            <button
              onClick={() => setStep('verify')}
              className="flex-1 py-3 px-4 bg-gradient-to-r from-saturn-600 to-saturn-700 hover:from-saturn-700 hover:to-saturn-800 text-white font-heading font-semibold rounded-xl shadow-lg shadow-saturn-500/30 hover:shadow-xl hover:shadow-saturn-500/40 transition-all duration-150 active:scale-[0.98]"
            >
              Next: Verify Code
            </button>
          </div>
        </div>
      )}

      {/* Verify View */}
      {step === 'verify' && (
        <div className="glass-neo border border-saturn-200/50 rounded-2xl p-6">
          <div className="text-center mb-6">
            <h3 className="font-heading font-bold text-saturn-900 text-xl mb-2">
              Verify Setup
            </h3>
            <p className="text-saturn-600">
              Enter the 6-digit code from your authenticator app
            </p>
          </div>

          <form onSubmit={handleVerifyAndEnable} className="max-w-sm mx-auto space-y-6">
            <div>
              <label htmlFor="verification-code" className="block text-sm font-medium text-saturn-900 mb-2">
                Verification Code
              </label>
              <input
                id="verification-code"
                type="text"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value.replace(/[^0-9]/g, ''))}
                maxLength={6}
                required
                className="block w-full px-4 py-3 border border-saturn-200 rounded-xl bg-white/50 text-saturn-900 text-center text-2xl font-mono tracking-widest placeholder-saturn-400 focus:outline-none focus:ring-2 focus:ring-saturn-500 focus:border-transparent transition-all"
                placeholder="000000"
              />
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setStep('setup')}
                className="flex-1 py-3 px-4 bg-saturn-100 hover:bg-saturn-200 text-saturn-700 font-heading font-semibold rounded-xl transition-all duration-150 active:scale-[0.98]"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={isLoading || verificationCode.length !== 6}
                className="flex-1 py-3 px-4 bg-gradient-to-r from-saturn-600 to-saturn-700 hover:from-saturn-700 hover:to-saturn-800 text-white font-heading font-semibold rounded-xl shadow-lg shadow-saturn-500/30 hover:shadow-xl hover:shadow-saturn-500/40 transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
              >
                {isLoading ? 'Verifying...' : 'Enable 2FA'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Info */}
      <div className="bg-gradient-to-br from-sun-50 to-saturn-50 border border-sun-200 rounded-xl p-4">
        <h4 className="font-heading font-bold text-saturn-900 text-sm mb-2">
          What is Two-Factor Authentication?
        </h4>
        <ul className="text-xs text-saturn-700 space-y-1">
          <li>• Adds an extra layer of security beyond just your password</li>
          <li>• Requires a time-based code from your mobile device</li>
          <li>• Protects your account even if your password is compromised</li>
          <li>• Recommended for all accounts with sensitive data</li>
        </ul>
      </div>
    </div>
  );
}
