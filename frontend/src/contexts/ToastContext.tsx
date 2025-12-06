/**
 * Toast Notification Context
 * Global toast notifications for the app
 */

import { createContext, useContext, useState, ReactNode, useCallback } from 'react';
import { 
  CheckCircleIcon, 
  XCircleIcon, 
  InformationCircleIcon,
  ExclamationTriangleIcon,
  XMarkIcon 
} from '@heroicons/react/24/outline';

type ToastType = 'success' | 'error' | 'info' | 'warning';

interface Toast {
  id: string;
  type: ToastType;
  message: string;
}

interface ToastContextType {
  showToast: (message: string, type: ToastType) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
  warning: (message: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((message: string, type: ToastType) => {
    const id = Math.random().toString(36).substr(2, 9);
    const newToast = { id, type, message };
    
    setToasts((prev) => [...prev, newToast]);

    // Auto remove after 5 seconds
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const contextValue: ToastContextType = {
    showToast,
    success: (message) => showToast(message, 'success'),
    error: (message) => showToast(message, 'error'),
    info: (message) => showToast(message, 'info'),
    warning: (message) => showToast(message, 'warning'),
  };

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      
      {/* Toast Container */}
      <div className="fixed top-4 right-4 z-50 space-y-2 max-w-md">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  const config = {
    success: {
      icon: CheckCircleIcon,
      bg: 'from-moon-500/20 to-moon-600/20',
      border: 'border-moon-500/30',
      text: 'text-moon-400',
      iconBg: 'bg-moon-500/20',
    },
    error: {
      icon: XCircleIcon,
      bg: 'from-mars-500/20 to-mars-600/20',
      border: 'border-mars-500/30',
      text: 'text-mars-400',
      iconBg: 'bg-mars-500/20',
    },
    warning: {
      icon: ExclamationTriangleIcon,
      bg: 'from-sun-500/20 to-sun-600/20',
      border: 'border-sun-500/30',
      text: 'text-sun-400',
      iconBg: 'bg-sun-500/20',
    },
    info: {
      icon: InformationCircleIcon,
      bg: 'from-saturn-500/20 to-saturn-600/20',
      border: 'border-saturn-500/30',
      text: 'text-saturn-400',
      iconBg: 'bg-saturn-500/20',
    },
  };

  const { icon: Icon, bg, border, text, iconBg } = config[toast.type];

  return (
    <div
      className={`flex items-start gap-3 p-4 bg-gradient-to-r ${bg} backdrop-blur-xl border ${border} rounded-xl shadow-lg animate-slideIn`}
    >
      <div className={`p-2 ${iconBg} rounded-lg flex-shrink-0`}>
        <Icon className={`w-5 h-5 ${text}`} />
      </div>
      <p className="flex-1 text-sm text-pearl-100">{toast.message}</p>
      <button
        onClick={onClose}
        className="p-1 hover:bg-pearl-700/30 rounded transition-colors flex-shrink-0"
      >
        <XMarkIcon className="w-4 h-4 text-pearl-400" />
      </button>
    </div>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}
