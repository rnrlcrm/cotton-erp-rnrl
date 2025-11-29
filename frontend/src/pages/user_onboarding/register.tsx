/**
 * User Registration Page
 *
 * Supports two registration flows:
 * 1. INTERNAL users: Email + Password with password policy enforcement
 * 2. EXTERNAL users: Mobile OTP based registration
 */

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate, Link } from 'react-router-dom';
import { authService } from '../../services/auth/auth.service';

// Password validation schema (matches backend InternalUserSignupRequest)
const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
  .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
  .regex(/\d/, 'Password must contain at least one number');

// Email signup schema
const emailSignupSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: passwordSchema,
  confirmPassword: z.string(),
  fullName: z.string().min(2, 'Name must be at least 2 characters').optional(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
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

type EmailSignupForm = z.infer<typeof emailSignupSchema>;
type MobileOtpForm = z.infer<typeof mobileOtpSchema>;
type OtpVerifyForm = z.infer<typeof otpVerifySchema>;

type RegistrationType = 'email' | 'mobile';

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const [registrationType, setRegistrationType] = useState<RegistrationType>('email');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // OTP flow states
  const [otpSent, setOtpSent] = useState(false);
  const [mobileNumber, setMobileNumber] = useState('');
  const [otpExpiresIn, setOtpExpiresIn] = useState(300);

  // Email signup form
  const emailForm = useForm<EmailSignupForm>({
    resolver: zodResolver(emailSignupSchema),
    defaultValues: {
      email: '',
      password: '',
      confirmPassword: '',
      fullName: '',
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

  // Handle email/password registration
  const handleEmailSignup = async (data: EmailSignupForm) => {
    setIsLoading(true);
    setError(null);

    try {
      await authService.signupInternal({
        email: data.email,
        password: data.password,
        full_name: data.fullName,
      });

      setSuccess('Account created successfully! Please log in.');
      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Registration failed. Please try again.');
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
      navigate('/dashboard');
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

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Create your account
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Or{' '}
          <Link to="/login" className="font-medium text-indigo-600 hover:text-indigo-500">
            sign in to your existing account
          </Link>
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          {/* Registration type selector */}
          <div className="flex mb-6 bg-gray-100 rounded-lg p-1">
            <button
              type="button"
              onClick={() => setRegistrationType('email')}
              className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
                registrationType === 'email'
                  ? 'bg-white text-indigo-600 shadow'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Email (Internal)
            </button>
            <button
              type="button"
              onClick={() => setRegistrationType('mobile')}
              className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
                registrationType === 'mobile'
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

          {/* Email Registration Form */}
          {registrationType === 'email' && (
            <form onSubmit={emailForm.handleSubmit(handleEmailSignup)} className="space-y-6">
              <div>
                <label htmlFor="fullName" className="block text-sm font-medium text-gray-700">
                  Full Name (Optional)
                </label>
                <input
                  {...emailForm.register('fullName')}
                  type="text"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="John Doe"
                />
                {emailForm.formState.errors.fullName && (
                  <p className="mt-1 text-sm text-red-600">
                    {emailForm.formState.errors.fullName.message}
                  </p>
                )}
              </div>

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
                  autoComplete="new-password"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                />
                {emailForm.formState.errors.password && (
                  <p className="mt-1 text-sm text-red-600">
                    {emailForm.formState.errors.password.message}
                  </p>
                )}
                <p className="mt-1 text-xs text-gray-500">
                  Min 8 chars, 1 uppercase, 1 lowercase, 1 number
                </p>
              </div>

              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
                  Confirm Password
                </label>
                <input
                  {...emailForm.register('confirmPassword')}
                  type="password"
                  autoComplete="new-password"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                />
                {emailForm.formState.errors.confirmPassword && (
                  <p className="mt-1 text-sm text-red-600">
                    {emailForm.formState.errors.confirmPassword.message}
                  </p>
                )}
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Creating Account...' : 'Create Account'}
              </button>
            </form>
          )}

          {/* Mobile OTP Registration Form */}
          {registrationType === 'mobile' && !otpSent && (
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
                For business partners. OTP will be sent to your registered mobile number.
              </p>
            </form>
          )}

          {/* OTP Verification Form */}
          {registrationType === 'mobile' && otpSent && (
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
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
