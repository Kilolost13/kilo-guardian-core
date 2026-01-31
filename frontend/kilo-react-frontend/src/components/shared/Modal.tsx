import React from 'react';

interface ModalProps {
  title?: string;
  open: boolean;
  onClose: () => void;
  children?: React.ReactNode;
}

export const Modal = ({ title, open, onClose, children }: ModalProps): React.ReactElement | null => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      <div className="bg-dark-card border-2 border-dark-border rounded-xl p-6 z-10 w-full max-w-2xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-zombie-green">{title}</h3>
          <button onClick={onClose} className="text-zombie-green hover:text-terminal-green">✕</button>
        </div>

        <div className="max-h-[60vh] overflow-auto text-sm text-gray-200">
          {children}
        </div>
      </div>
    </div>
  );
};
