/**
 * Inactivity Timeout Manager
 * Monitors user activity and shows warning before auto-logout
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { ExclamationTriangleIcon, ClockIcon } from '@heroicons/react/24/outline';

const INACTIVITY_TIMEOUT = 30 * 60 * 1000; // 30 minutes
const WARNING_BEFORE = 5 * 60 * 1000; // 5 minutes warning
const WARNING_TIMEOUT = INACTIVITY_TIMEOUT - WARNING_BEFORE;

export function InactivityMonitor() {
  const { logout, isAuthenticated } = useAuth();
  const [showWarning, setShowWarning] = useState(false);
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  
  const warningTimerRef = useRef<number>();
  const logoutTimerRef = useRef<number>();
  const countdownIntervalRef = useRef<number>();

  const resetTimers = useCallback(() => {
    // Clear existing timers
    if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
    if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);
    if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
    
    setShowWarning(false);

    if (!isAuthenticated) return;

    // Set warning timer
    warningTimerRef.current = setTimeout(() => {
      setShowWarning(true);
      setRemainingSeconds(WARNING_BEFORE / 1000);

      // Start countdown
      countdownIntervalRef.current = setInterval(() => {
        setRemainingSeconds(prev => {
          if (prev <= 1) {
            if (countdownIntervalRef.current) {
              clearInterval(countdownIntervalRef.current);
            }
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }, WARNING_TIMEOUT);

    // Set auto-logout timer
    logoutTimerRef.current = setTimeout(() => {
      handleAutoLogout();
    }, INACTIVITY_TIMEOUT);
  }, [isAuthenticated]);

  const handleAutoLogout = useCallback(() => {
    setShowWarning(false);
    logout();
  }, [logout]);

  const handleStayLoggedIn = useCallback(() => {
    resetTimers();
  }, [resetTimers]);

  // Monitor user activity
  useEffect(() => {
    if (!isAuthenticated) return;

    const activityEvents = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click'];
    
    const handleActivity = () => {
      if (!showWarning) {
        resetTimers();
      }
    };

    // Add event listeners
    activityEvents.forEach(event => {
      window.addEventListener(event, handleActivity, { passive: true });
    });

    // Initial timer setup
    resetTimers();

    // Cleanup
    return () => {
      activityEvents.forEach(event => {
        window.removeEventListener(event, handleActivity);
      });
      if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
      if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
    };
  }, [isAuthenticated, showWarning, resetTimers]);

  if (!showWarning || !isAuthenticated) return null;

  const minutes = Math.floor(remainingSeconds / 60);
  const seconds = remainingSeconds % 60;

  return (
    <div className="fixed inset-0 bg-space-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fadeIn">
      <div className="glass-neo border-2 border-sun-400/50 rounded-2xl p-8 max-w-md w-full shadow-2xl shadow-sun-500/20 animate-scaleIn">
        {/* Warning icon */}
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-sun-400 to-mars-500 flex items-center justify-center shadow-lg shadow-sun-500/30">
            <ExclamationTriangleIcon className="w-10 h-10 text-white" />
          </div>
        </div>

        {/* Title */}
        <h3 className="text-2xl font-heading font-bold text-space-900 text-center mb-3">
          Session Timeout Warning
        </h3>

        {/* Message */}
        <p className="text-saturn-700 text-center mb-6">
          You've been inactive for a while. Your session will expire soon for security reasons.
        </p>

        {/* Countdown */}
        <div className="bg-gradient-to-br from-sun-50 to-mars-50 border border-sun-200 rounded-xl p-4 mb-6">
          <div className="flex items-center justify-center gap-2 text-sun-700">
            <ClockIcon className="w-5 h-5" />
            <span className="text-lg font-heading font-bold">
              {minutes}:{seconds.toString().padStart(2, '0')}
            </span>
          </div>
          <p className="text-xs text-center text-sun-600 mt-1">
            Auto-logout in {minutes} minute{minutes !== 1 ? 's' : ''} {seconds} second{seconds !== 1 ? 's' : ''}
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={handleAutoLogout}
            className="flex-1 py-3 px-4 bg-saturn-100 hover:bg-saturn-200 text-saturn-700 font-heading font-semibold rounded-xl transition-all duration-150 active:scale-[0.98]"
          >
            Logout Now
          </button>
          <button
            onClick={handleStayLoggedIn}
            className="flex-1 py-3 px-4 bg-gradient-to-r from-saturn-600 to-saturn-700 hover:from-saturn-700 hover:to-saturn-800 text-white font-heading font-semibold rounded-xl shadow-lg shadow-saturn-500/30 hover:shadow-xl hover:shadow-saturn-500/40 transition-all duration-150 active:scale-[0.98]"
          >
            Stay Logged In
          </button>
        </div>
      </div>
    </div>
  );
}
