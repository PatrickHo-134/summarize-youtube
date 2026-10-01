import React, { useEffect } from 'react';
import { Authenticator, ThemeProvider, createTheme } from '@aws-amplify/ui-react';

const appTheme = createTheme({
  name: 'yt-summarizer-theme',
  tokens: {
    colors: {
      brand: {
        primary: {
          10:  { value: '#eef2ff' },
          20:  { value: '#e0e7ff' },
          40:  { value: '#c7d2fe' },
          60:  { value: '#818cf8' },
          80:  { value: '#6366f1' },
          90:  { value: '#4f46e5' },
          100: { value: '#3730a3' },
        },
      },
    },
    components: {
      authenticator: {
        router: {
          borderWidth: { value: '1px' },
          borderStyle: { value: 'solid' },
          borderColor: { value: '#e5e7eb' },
          backgroundColor: { value: '#ffffff' },
          boxShadow: { value: '0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -1px rgba(0,0,0,0.04)' },
        },
      },
      button: {
        borderRadius: { value: '9999px' },
        primary: {
          backgroundColor: { value: '#4f46e5' },
          borderColor: { value: '#4f46e5' },
          borderStyle: { value: 'solid' },
          borderWidth: { value: '1px' },
          color: { value: '#ffffff' },
          _hover: {
            backgroundColor: { value: '#4338ca' },
            borderColor: { value: '#4338ca' },
            color: { value: '#ffffff' },
          },
          _focus: {
            backgroundColor: { value: '#4338ca' },
            borderColor: { value: '#4338ca' },
            color: { value: '#ffffff' },
            boxShadow: { value: '0 0 0 2px rgba(79,70,229,0.35)' },
          },
          _active: {
            backgroundColor: { value: '#3730a3' },
            borderColor: { value: '#3730a3' },
            color: { value: '#ffffff' },
          },
        },
        link: {
          backgroundColor: { value: 'transparent' },
          borderColor: { value: 'transparent' },
          borderWidth: { value: '0' },
          color: { value: '#4f46e5' },
          _hover: {
            backgroundColor: { value: 'transparent' },
            borderColor: { value: 'transparent' },
            color: { value: '#4338ca' },
          },
          _focus: {
            backgroundColor: { value: 'transparent' },
            borderColor: { value: 'transparent' },
            color: { value: '#4338ca' },
            boxShadow: { value: 'none' },
          },
          _active: {
            backgroundColor: { value: 'transparent' },
            borderColor: { value: 'transparent' },
            color: { value: '#3730a3' },
          },
        },
      },
      fieldcontrol: {
        borderRadius: { value: '0.5rem' },
        borderColor: { value: '#e5e7eb' },
        borderWidth: { value: '1px' },
        borderStyle: { value: 'solid' },
        color: { value: '#111827' },
        fontSize: { value: '0.875rem' },
        _focus: {
          borderColor: { value: '#4f46e5' },
          boxShadow: { value: '0 0 0 2px rgba(79,70,229,0.2)' },
        },
      },
      field: {
        label: {
          color: { value: '#374151' },
        },
      },
      tabs: {
        borderColor: { value: '#e5e7eb' },
        borderStyle: { value: 'solid' },
        borderWidth: { value: '0 0 1px 0' },
        item: {
          color: { value: '#6b7280' },
          fontSize: { value: '0.875rem' },
          fontWeight: { value: '500' },
          borderColor: { value: 'transparent' },
          _hover: {
            color: { value: '#374151' },
            backgroundColor: { value: 'transparent' },
            borderColor: { value: 'transparent' },
          },
          _focus: {
            color: { value: '#4f46e5' },
            borderColor: { value: '#4f46e5' },
            boxShadow: { value: 'none' },
          },
          _active: {
            color: { value: '#4f46e5' },
            borderColor: { value: '#4f46e5' },
            backgroundColor: { value: 'transparent' },
          },
        },
      },
    },
    fonts: {
      default: {
        variable: { value: "system-ui, 'Segoe UI', Roboto, sans-serif" },
        static: { value: "system-ui, 'Segoe UI', Roboto, sans-serif" },
      },
    },
    radii: {
      small: { value: '0.375rem' },
      medium: { value: '0.5rem' },
      large: { value: '0.75rem' },
      xl: { value: '1rem' },
    },
    fontSizes: {
      small: { value: '0.75rem' },
      medium: { value: '0.875rem' },
      large: { value: '1rem' },
    },
    fontWeights: {
      medium: { value: '500' },
      semibold: { value: '600' },
      bold: { value: '700' },
    },
  },
});

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  message?: string | null;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onSuccess, message }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm overflow-y-auto">
      <div className="inline-flex flex-col mx-auto my-auto">
        <div className="flex justify-end mb-1">
          <button
            onClick={onClose}
            className="flex items-center justify-center w-7 h-7 rounded-full bg-white border border-gray-200 shadow-sm text-gray-400 hover:text-gray-700 hover:border-gray-300 transition cursor-pointer text-base leading-none"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        {message && (
          <div className="mb-3 rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800 text-center font-medium">
            {message}
          </div>
        )}
        <ThemeProvider theme={appTheme} colorMode="light">
          <Authenticator>
            {({ user }) => <AuthSuccessTrigger user={user} onSuccess={onSuccess} />}
          </Authenticator>
        </ThemeProvider>
      </div>
    </div>
  );
};

interface AuthSuccessTriggerProps {
  user: unknown;
  onSuccess: () => void;
}

const AuthSuccessTrigger: React.FC<AuthSuccessTriggerProps> = ({ user, onSuccess }) => {
  useEffect(() => {
    if (user) {
      onSuccess();
    }
  }, [user, onSuccess]);

  return null;
};
