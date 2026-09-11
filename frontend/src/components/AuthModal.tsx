import React, { useEffect } from 'react';
import { Authenticator } from '@aws-amplify/ui-react';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onSuccess }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative">
        <button
          onClick={onClose}
          className="absolute top-2 right-2 z-10 text-gray-500 hover:text-gray-800 text-xl font-bold cursor-pointer"
        >
          ✕
        </button>
        <Authenticator>
          {({ user }) => <AuthSuccessTrigger user={user} onSuccess={onSuccess} />}
        </Authenticator>
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
