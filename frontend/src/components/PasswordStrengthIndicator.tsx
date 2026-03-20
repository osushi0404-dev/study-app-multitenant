import React from 'react';

interface PasswordStrengthProps {
  strength: {
    strength: 'weak' | 'medium' | 'strong';
    requirements: {
      minLength: boolean;
      hasUpperCase: boolean;
      hasLowerCase: boolean;
      hasNumber: boolean;
      hasSpecialChar: boolean;
    };
  } | null;
}

const getStrengthColor = (strength: 'weak' | 'medium' | 'strong'): string => {
  switch (strength) {
    case 'strong':
      return 'bg-green-600';
    case 'medium':
      return 'bg-yellow-500';
    case 'weak':
      return 'bg-red-500';
    default:
      return 'bg-gray-300';
  }
};

const getStrengthLabel = (strength: 'weak' | 'medium' | 'strong'): string => {
  switch (strength) {
    case 'strong':
      return '強い';
    case 'medium':
      return '中程度';
    case 'weak':
      return '弱い';
    default:
      return '';
  }
};

export const PasswordStrengthIndicator: React.FC<PasswordStrengthProps> = ({
  strength
}) => {
  if (!strength) return null;

  return (
    <div className="mt-2">
      <div className="flex items-center space-x-2 mb-2">
        <div className="flex-1 bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${getStrengthColor(
              strength.strength
            )}`}
            style={{
              width:
                strength.strength === 'strong'
                  ? '100%'
                  : strength.strength === 'medium'
                  ? '66%'
                  : '33%'
            }}
          />
        </div>
        <span className="text-sm text-gray-600">
          {getStrengthLabel(strength.strength)}
        </span>
      </div>
      <ul className="space-y-1 text-sm">
        <li
          className="flex items-center"
          style={{
            color: strength.requirements.minLength ? '#22c55e' : '#ef4444'
          }}
        >
          <span className="mr-2">
            {strength.requirements.minLength ? '✓' : '✗'}
          </span>
          8文字以上
        </li>
        <li
          className="flex items-center"
          style={{
            color: strength.requirements.hasUpperCase ? '#22c55e' : '#ef4444'
          }}
        >
          <span className="mr-2">
            {strength.requirements.hasUpperCase ? '✓' : '✗'}
          </span>
          大文字を含む
        </li>
        <li
          className="flex items-center"
          style={{
            color: strength.requirements.hasLowerCase ? '#22c55e' : '#ef4444'
          }}
        >
          <span className="mr-2">
            {strength.requirements.hasLowerCase ? '✓' : '✗'}
          </span>
          小文字を含む
        </li>
        <li
          className="flex items-center"
          style={{
            color: strength.requirements.hasNumber ? '#22c55e' : '#ef4444'
          }}
        >
          <span className="mr-2">
            {strength.requirements.hasNumber ? '✓' : '✗'}
          </span>
          数字を含む
        </li>
      </ul>
    </div>
  );
};