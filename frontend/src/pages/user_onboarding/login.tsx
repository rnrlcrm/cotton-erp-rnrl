/**
 * User Login Page
 *
 * Supports two login flows:
 * 1. INTERNAL users: Email + Password
 * 2. EXTERNAL users: Mobile OTP
 */

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { authService } from '../../services/auth/auth.service';

// Email login schema
const emailLoginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});

// Mobile OTP schema
const mobileOtpSchema = z.object({
  mobileNumber: z
    .string()
    .regex(/^\+?[1-9]\d{9,14}$/, 'Please enter a valid mobile number'),
  countryCode: z.string().default('+91'),
});

const otpVerifySchema = z.object({
  otp: z.string().length(6, 'OTP must be 6 digits').regex(/^\d+$/, 'OTP must contain only digits'),
});

// 2FA PIN schema
const pinVerifySchema = z.object({
  pin: z.string().min(4, 'PIN must be at least 4 digits').max(6, 'PIN must be at most 6 digits'),
});

type EmailLoginForm = z.infer<typeof emailLoginSchema>;
type MobileOtpForm = z.infer<typeof mobileOtpSchema>;
type OtpVerifyForm = z.infer<typeof otpVerifySchema>;
type PinVerifyForm = z.infer<typeof pinVerifySchema>;

type LoginType = 'email' | 'mobile';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: Location })?.from?.pathname || '/dashboard';

  const [loginType, setLoginType] = useState<LoginType>('email');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // 2FA states
  const [requires2FA, setRequires2FA] = useState(false);
  const [email2FA, setEmail2FA] = useState('');

  // OTP flow states
  const [otpSent, setOtpSent] = useState(false);
  const [mobileNumber, setMobileNumber] = useState('');
  const [otpExpiresIn, setOtpExpiresIn] = useState(300);

  // Email login form
  const emailForm = useForm<EmailLoginForm>({
    resolver: zodResolver(emailLoginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  });

  // Mobile OTP form
  const mobileForm = useForm<MobileOtpForm>({
    resolver: zodResolver(mobileOtpSchema),
    defaultValues: {
      mobileNumber: '',
      countryCode: '+91',
    },
  });

  // OTP verification form
  const otpForm = useForm<OtpVerifyForm>({
    resolver: zodResolver(otpVerifySchema),
    defaultValues: {
      otp: '',
    },
  });

  // 2FA PIN form
  const pinForm = useForm<PinVerifyForm>({
    resolver: zodResolver(pinVerifySchema),
    defaultValues: {
      pin: '',
    },
  });

  // Handle email/password login
  const handleEmailLogin = async (data: EmailLoginForm) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await authService.login({
        email: data.email,
        password: data.password,
      });

      // Check if 2FA is required
      if ('two_fa_required' in response && response.two_fa_required) {
        setRequires2FA(true);
        setEmail2FA(data.email);
        setSuccess('Please enter your 2FA PIN');
      } else {
        setSuccess('Login successful!');
        navigate(from, { replace: true });
      }
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle 2FA PIN verification
  const handlePinVerify = async (data: PinVerifyForm) => {
    setIsLoading(true);
    setError(null);

    try {
      await authService.verify2FA(email2FA, data.pin);
      setSuccess('Login successful!');
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Invalid PIN. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle sending OTP
  const handleSendOtp = async (data: MobileOtpForm) => {
    setIsLoading(true);
    setError(null);

    try {
      const fullMobile = data.mobileNumber.startsWith('+')
        ? data.mobileNumber
        : `${data.countryCode}${data.mobileNumber}`;

      const response = await authService.sendOTP({
        mobile_number: fullMobile,
        country_code: data.countryCode,
      });

      setMobileNumber(fullMobile);
      setOtpSent(true);
      setOtpExpiresIn(response.expires_in_seconds);
      setSuccess(response.message);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Failed to send OTP. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle OTP verification
  const handleVerifyOtp = async (data: OtpVerifyForm) => {
    setIsLoading(true);
    setError(null);

    try {
      await authService.verifyOTP({
        mobile_number: mobileNumber,
        otp: data.otp,
      });

      setSuccess('Login successful!');
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Invalid OTP. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Reset OTP flow
  const handleResetOtp = () => {
    setOtpSent(false);
    setMobileNumber('');
    otpForm.reset();
  };

  // Reset 2FA flow
  const handleReset2FA = () => {
    setRequires2FA(false);
    setEmail2FA('');
    pinForm.reset();
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Sign in to your account
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Or{' '}
          <Link to="/register" className="font-medium text-indigo-600 hover:text-indigo-500">
            create a new account
          </Link>
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          {/* 2FA PIN Entry */}
          {requires2FA && (
            <form onSubmit={pinForm.handleSubmit(handlePinVerify)} className="space-y-6">
              <div className="text-center mb-4">
                <p className="text-sm text-gray-600">2FA Required</p>
                <p className="font-medium text-gray-900">{email2FA}</p>
              </div>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}

              <div>
                <label htmlFor="pin" className="block text-sm font-medium text-gray-700">
                  Enter PIN
                </label>
                <input
                  {...pinForm.register('pin')}
                  type="password"
                  maxLength={6}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-center text-2xl tracking-widest"
                  placeholder="••••••"
                />
                {pinForm.formState.errors.pin && (
                  <p className="mt-1 text-sm text-red-600">
                    {pinForm.formState.errors.pin.message}
                  </p>
                )}
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
              >
                {isLoading ? 'Verifying...' : 'Verify PIN'}
              </button>

              <button
                type="button"
                onClick={handleReset2FA}
                className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                Back to Login
              </button>
            </form>
          )}

          {!requires2FA && (
            <>
              {/* Login type selector */}
              <div className="flex mb-6 bg-gray-100 rounded-lg p-1">
                <button
                  type="button"
                  onClick={() => setLoginType('email')}
                  className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
                    loginType === 'email'
                      ? 'bg-white text-indigo-600 shadow'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Email (Internal)
                </button>
                <button
                  type="button"
                  onClick={() => setLoginType('mobile')}
                  className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
                    loginType === 'mobile'
                      ? 'bg-white text-indigo-600 shadow'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Mobile OTP (Partner)
                </button>
              </div>

              {/* Error message */}
              {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}

              {/* Success message */}
              {success && (
                <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md">
                  <p className="text-sm text-green-600">{success}</p>
                </div>
              )}

              {/* Email Login Form */}
              {loginType === 'email' && (
                <form onSubmit={emailForm.handleSubmit(handleEmailLogin)} className="space-y-6">
                  <div>
                    <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                      Email Address
                    </label>
                    <input
                      {...emailForm.register('email')}
                      type="email"
                      autoComplete="email"
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                      placeholder="you@example.com"
                    />
                    {emailForm.formState.errors.email && (
                      <p className="mt-1 text-sm text-red-600">
                        {emailForm.formState.errors.email.message}
                      </p>
                    )}
                  </div>

                  <div>
                    <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                      Password
                    </label>
                    <input
                      {...emailForm.register('password')}
                      type="password"
                      autoComplete="current-password"
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    />
                    {emailForm.formState.errors.password && (
                      <p className="mt-1 text-sm text-red-600">
                        {emailForm.formState.errors.password.message}
                      </p>
                    )}
                  </div>

                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading ? 'Signing in...' : 'Sign In'}
                  </button>
                </form>
              )}

              {/* Mobile OTP Login Form */}
              {loginType === 'mobile' && !otpSent && (
                <form onSubmit={mobileForm.handleSubmit(handleSendOtp)} className="space-y-6">
                  <div>
                    <label htmlFor="countryCode" className="block text-sm font-medium text-gray-700">
                      Country Code
                    </label>
                    <select
                      {...mobileForm.register('countryCode')}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    >
                      <option value="+91">India (+91)</option>
                      <option value="+1">USA (+1)</option>
                      <option value="+44">UK (+44)</option>
                      <option value="+971">UAE (+971)</option>
                    </select>
                  </div>

                  <div>
                    <label htmlFor="mobileNumber" className="block text-sm font-medium text-gray-700">
                      Mobile Number
                    </label>
                    <input
                      {...mobileForm.register('mobileNumber')}
                      type="tel"
                      autoComplete="tel"
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                      placeholder="9876543210"
                    />
                    {mobileForm.formState.errors.mobileNumber && (
                      <p className="mt-1 text-sm text-red-600">
                        {mobileForm.formState.errors.mobileNumber.message}
                      </p>
                    )}
                  </div>

                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading ? 'Sending OTP...' : 'Send OTP'}
                  </button>

                  <p className="text-xs text-gray-500 text-center">
                    For business partners. OTP will be sent to your registered mobile.
                  </p>
                </form>
              )}

              {/* OTP Verification Form */}
              {loginType === 'mobile' && otpSent && (
                <form onSubmit={otpForm.handleSubmit(handleVerifyOtp)} className="space-y-6">
                  <div className="text-center mb-4">
                    <p className="text-sm text-gray-600">OTP sent to</p>
                    <p className="font-medium text-gray-900">{mobileNumber}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      Expires in {Math.floor(otpExpiresIn / 60)}:{(otpExpiresIn % 60).toString().padStart(2, '0')} minutes
                    </p>
                  </div>

                  <div>
                    <label htmlFor="otp" className="block text-sm font-medium text-gray-700">
                      Enter OTP
                    </label>
                    <input
                      {...otpForm.register('otp')}
                      type="text"
                      maxLength={6}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-center text-2xl tracking-widest"
                      placeholder="000000"
                    />
                    {otpForm.formState.errors.otp && (
                      <p className="mt-1 text-sm text-red-600">
                        {otpForm.formState.errors.otp.message}
                      </p>
                    )}
                  </div>

                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading ? 'Verifying...' : 'Verify OTP'}
                  </button>

                  <button
                    type="button"
                    onClick={handleResetOtp}
                    className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    Change Number
                  </button>
                </form>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
