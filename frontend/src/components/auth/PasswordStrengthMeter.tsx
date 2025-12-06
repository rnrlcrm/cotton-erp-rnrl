/**
 * Password Strength Meter
 * Visual indicator for password strength with validation rules
 */

import { useMemo } from 'react';
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';

interface PasswordStrengthMeterProps {
  password: string;
  showRequirements?: boolean;
}

interface StrengthResult {
  score: number; // 0-4
  label: string;
  color: string;
  percentage: number;
  requirements: {
    minLength: boolean;
    hasUppercase: boolean;
    hasLowercase: boolean;
    hasNumber: boolean;
    hasSpecial: boolean;
  };
}

export function PasswordStrengthMeter({ password, showRequirements = true }: PasswordStrengthMeterProps) {
  const strength = useMemo((): StrengthResult => {
    if (!password) {
      return {
        score: 0,
        label: 'No password',
        color: 'bg-saturn-200',
        percentage: 0,
        requirements: {
          minLength: false,
          hasUppercase: false,
          hasLowercase: false,
          hasNumber: false,
          hasSpecial: false,
        },
      };
    }

    const requirements = {
      minLength: password.length >= 8,
      hasUppercase: /[A-Z]/.test(password),
      hasLowercase: /[a-z]/.test(password),
      hasNumber: /[0-9]/.test(password),
      hasSpecial: /[^A-Za-z0-9]/.test(password),
    };

    // Calculate score
    let score = 0;
    if (requirements.minLength) score++;
    if (requirements.hasUppercase) score++;
    if (requirements.hasLowercase) score++;
    if (requirements.hasNumber) score++;
    if (requirements.hasSpecial) score++;

    // Determine strength label and color
    let label = '';
    let color = '';
    let percentage = 0;

    if (score === 0) {
      label = 'Very Weak';
      color = 'bg-mars-500';
      percentage = 20;
    } else if (score === 1 || score === 2) {
      label = 'Weak';
      color = 'bg-sun-500';
      percentage = 40;
    } else if (score === 3) {
      label = 'Fair';
      color = 'bg-sun-400';
      percentage = 60;
    } else if (score === 4) {
      label = 'Good';
      color = 'bg-saturn-500';
      percentage = 80;
    } else {
      label = 'Strong';
      color = 'bg-emerald-500';
      percentage = 100;
    }

    return { score, label, color, percentage, requirements };
  }, [password]);

  return (
    <div className="space-y-3">
      {/* Strength bar */}
      <div>
        <div className="flex justify-between items-center mb-1.5">
          <span className="text-xs font-medium text-saturn-700">Password Strength</span>
          <span className={`text-xs font-semibold ${
            strength.score === 0 ? 'text-saturn-400' :
            strength.score <= 2 ? 'text-mars-600' :
            strength.score === 3 ? 'text-sun-600' :
            strength.score === 4 ? 'text-saturn-600' :
            'text-emerald-600'
          }`}>
            {strength.label}
          </span>
        </div>
        
        <div className="h-2 bg-saturn-100 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${strength.color}`}
            style={{ width: `${strength.percentage}%` }}
          />
        </div>
      </div>

      {/* Requirements checklist */}
      {showRequirements && password && (
        <div className="space-y-1.5 text-xs">
          <RequirementItem
            met={strength.requirements.minLength}
            text="At least 8 characters"
          />
          <RequirementItem
            met={strength.requirements.hasUppercase}
            text="One uppercase letter (A-Z)"
          />
          <RequirementItem
            met={strength.requirements.hasLowercase}
            text="One lowercase letter (a-z)"
          />
          <RequirementItem
            met={strength.requirements.hasNumber}
            text="One number (0-9)"
          />
          <RequirementItem
            met={strength.requirements.hasSpecial}
            text="One special character (!@#$%^&*)"
          />
        </div>
      )}
    </div>
  );
}

function RequirementItem({ met, text }: { met: boolean; text: string }) {
  return (
    <div className={`flex items-center gap-2 ${met ? 'text-emerald-700' : 'text-saturn-500'}`}>
      {met ? (
        <CheckCircleIcon className="w-4 h-4 flex-shrink-0" />
      ) : (
        <XCircleIcon className="w-4 h-4 flex-shrink-0" />
      )}
      <span>{text}</span>
    </div>
  );
}
