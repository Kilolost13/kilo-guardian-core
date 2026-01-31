import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export const Card: React.FC<CardProps> = ({ children, className = '', onClick }) => {
  return (
    <div
      className={`bg-dark-card border-2 border-dark-border rounded-xl shadow-md p-6 ${onClick ? 'cursor-pointer hover:shadow-lg hover:border-zombie-green transition-all' : ''} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
};
