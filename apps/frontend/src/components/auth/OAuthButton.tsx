'use client';

import React, { useState } from 'react';
import { FaGithub, FaGoogle, FaMicrosoft } from 'react-icons/fa';
import { OAuthProvider } from '../../lib/auth/types';

interface OAuthButtonProps {
  provider: OAuthProvider;
  onClick: (provider: OAuthProvider) => void;
  disabled?: boolean;
  isLoading?: boolean;
}

interface ProviderConfig {
  name: string;
  icon: React.ElementType;
  bgColor: string;
  hoverColor: string;
  textColor: string;
  border?: boolean;
}

const providerConfig: Record<OAuthProvider, ProviderConfig> = {
  github: {
    name: 'GitHub',
    // @ts-expect-error React 19 type compatibility with react-icons
    icon: FaGithub,
    bgColor: '#24292e',
    hoverColor: '#1a1e22',
    textColor: '#ffffff',
  },
  google: {
    name: 'Google',
    // @ts-expect-error React 19 type compatibility with react-icons
    icon: FaGoogle,
    bgColor: '#ffffff',
    hoverColor: '#f8f9fa',
    textColor: '#3c4043',
    border: true,
  },
  microsoft: {
    name: 'Microsoft',
    // @ts-expect-error React 19 type compatibility with react-icons
    icon: FaMicrosoft,
    bgColor: '#00BCF2',
    hoverColor: '#0099cc',
    textColor: '#ffffff',
  },
};

export function OAuthButton({ provider, onClick, disabled = false, isLoading = false }: OAuthButtonProps) {
  const [isHovered, setIsHovered] = useState(false);
  const config = providerConfig[provider];
  const Icon = config.icon;

  const handleClick = () => {
    if (!disabled && !isLoading) {
      onClick(provider);
    }
  };

  const buttonStyle = {
    backgroundColor: isHovered ? config.hoverColor : config.bgColor,
    color: config.textColor,
    border: config.border ? '2px solid #dadce0' : 'none',
    borderColor: isHovered && config.border ? '#bdc1c6' : undefined,
  };

  return (
    <button
      onClick={handleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      disabled={disabled || isLoading}
      style={buttonStyle}
      className="btn-base btn-lg w-full transition-all duration-200 ease-in-out disabled:opacity-50 disabled:cursor-not-allowed hover:transform hover:translate-y-[-1px] hover:shadow-lg"
      aria-label={`Sign in with ${config.name}`}
    >
      <div className="flex items-center justify-center gap-3">
        {isLoading ? (
          <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
        ) : (
          <Icon className="w-5 h-5" />
        )}
        <span className="font-medium">
          {isLoading ? `Connecting to ${config.name}...` : `Continue with ${config.name}`}
        </span>
      </div>
    </button>
  );
}