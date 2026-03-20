import React, { forwardRef } from 'react';
import {
  Button as MuiButton,
  TextField as MuiTextField,
  Card as MuiCard,
  Typography as MuiTypography,
  ButtonProps,
  TextFieldProps,
  CardProps,
  TypographyProps,
  Alert,
  AlertProps
} from '@mui/material';
import { useAccessibility } from './AccessibilityProvider';

// アクセシブルなボタンコンポーネント
export const AccessibleButton = forwardRef<HTMLButtonElement, ButtonProps & {
  announceOnClick?: string;
}>((props, ref) => {
  const { announceOnClick, onClick, children, ...otherProps } = props;
  const { speak } = useAccessibility();

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    if (announceOnClick) {
      speak(announceOnClick);
    }
    if (onClick) {
      onClick(event);
    }
  };

  return (
    <MuiButton
      ref={ref}
      onClick={handleClick}
      className="touch-target"
      {...otherProps}
    >
      {children}
    </MuiButton>
  );
});

AccessibleButton.displayName = 'AccessibleButton';

// アクセシブルなテキストフィールドコンポーネント
export const AccessibleTextField = forwardRef<HTMLDivElement, TextFieldProps & {
  announceOnFocus?: string;
  announceOnError?: string;
}>((props, ref) => {
  const { announceOnFocus, announceOnError, onFocus, error, helperText, ...otherProps } = props;
  const { speak } = useAccessibility();

  const handleFocus = (event: React.FocusEvent<HTMLInputElement>) => {
    if (announceOnFocus) {
      speak(announceOnFocus);
    }
    if (onFocus) {
      onFocus(event);
    }
  };

  React.useEffect(() => {
    if (error && announceOnError) {
      speak(announceOnError);
    }
  }, [error, announceOnError, speak]);

  return (
    <MuiTextField
      ref={ref}
      onFocus={handleFocus}
      error={error}
      helperText={helperText}
      className={error ? 'error-state' : ''}
      inputProps={{
        'aria-invalid': error ? 'true' : 'false',
        'aria-describedby': helperText ? `${otherProps.id}-helper-text` : undefined,
        ...otherProps.inputProps
      }}
      FormHelperTextProps={{
        id: `${otherProps.id}-helper-text`,
        className: error ? 'error-text' : '',
        ...otherProps.FormHelperTextProps
      }}
      {...otherProps}
    />
  );
});

AccessibleTextField.displayName = 'AccessibleTextField';

// アクセシブルなカードコンポーネント
export const AccessibleCard = forwardRef<HTMLDivElement, CardProps & {
  heading?: string;
  announceOnHover?: string;
}>((props, ref) => {
  const { heading, announceOnHover, onMouseEnter, children, ...otherProps } = props;
  const { speak } = useAccessibility();

  const handleMouseEnter = (event: React.MouseEvent<HTMLDivElement>) => {
    if (announceOnHover) {
      speak(announceOnHover);
    }
    if (onMouseEnter) {
      onMouseEnter(event);
    }
  };

  return (
    <MuiCard
      ref={ref}
      onMouseEnter={handleMouseEnter}
      role="region"
      aria-label={heading}
      tabIndex={0}
      {...otherProps}
    >
      {children}
    </MuiCard>
  );
});

AccessibleCard.displayName = 'AccessibleCard';

// アクセシブルなタイポグラフィコンポーネント
export const AccessibleTypography = forwardRef<HTMLElement, TypographyProps & {
  announce?: boolean;
}>((props, ref) => {
  const { announce, children, ...otherProps } = props;
  const { speak } = useAccessibility();

  React.useEffect(() => {
    if (announce && typeof children === 'string') {
      speak(children);
    }
  }, [announce, children, speak]);

  return (
    <MuiTypography
      ref={ref}
      {...otherProps}
    >
      {children}
    </MuiTypography>
  );
});

AccessibleTypography.displayName = 'AccessibleTypography';

// アクセシブルなアラートコンポーネント
export const AccessibleAlert = forwardRef<HTMLDivElement, AlertProps & {
  announceImmediately?: boolean;
}>((props, ref) => {
  const { announceImmediately, children, severity, ...otherProps } = props;
  const { speak } = useAccessibility();

  React.useEffect(() => {
    if (announceImmediately && typeof children === 'string') {
      const severityText = severity ? `${severity}: ` : '';
      speak(`${severityText}${children}`);
    }
  }, [announceImmediately, children, severity, speak]);

  return (
    <Alert
      ref={ref}
      severity={severity}
      role="alert"
      aria-live="polite"
      className={`${severity}-state`}
      {...otherProps}
    >
      {children}
    </Alert>
  );
});

AccessibleAlert.displayName = 'AccessibleAlert';

// スクリーンリーダー専用テキスト
export const ScreenReaderOnly: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <span className="sr-only">
      {children}
    </span>
  );
};

// スキップリンク
export const SkipLink: React.FC<{ href: string; children: React.ReactNode }> = ({ 
  href, 
  children 
}) => {
  return (
    <a href={href} className="skip-link">
      {children}
    </a>
  );
};

// キーボードナビゲーション支援
export const KeyboardNavigationHelper: React.FC = () => {
  const [isKeyboardUser, setIsKeyboardUser] = React.useState(false);

  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Tab') {
        setIsKeyboardUser(true);
      }
    };

    const handleMouseDown = () => {
      setIsKeyboardUser(false);
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('mousedown', handleMouseDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('mousedown', handleMouseDown);
    };
  }, []);

  React.useEffect(() => {
    if (isKeyboardUser) {
      document.body.classList.add('keyboard-navigation');
    } else {
      document.body.classList.remove('keyboard-navigation');
    }
  }, [isKeyboardUser]);

  return null;
};

// フォーカス管理フック
export const useFocusManagement = () => {
  const focusElement = (selector: string) => {
    const element = document.querySelector(selector) as HTMLElement;
    if (element) {
      element.focus();
    }
  };

  const trapFocus = (containerSelector: string) => {
    const container = document.querySelector(containerSelector) as HTMLElement;
    if (!container) return;

    const focusableElements = container.querySelectorAll(
      'a[href], button, textarea, input[type="text"], input[type="radio"], input[type="checkbox"], select'
    ) as NodeListOf<HTMLElement>;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Tab') {
        if (event.shiftKey) {
          if (document.activeElement === firstElement) {
            event.preventDefault();
            lastElement.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            event.preventDefault();
            firstElement.focus();
          }
        }
      }
    };

    container.addEventListener('keydown', handleKeyDown);
    firstElement?.focus();

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
    };
  };

  return { focusElement, trapFocus };
};

// ライブリージョン管理フック
export const useLiveRegion = () => {
  const announceToScreenReader = (message: string, priority: 'polite' | 'assertive' = 'polite') => {
    const liveRegion = document.createElement('div');
    liveRegion.setAttribute('aria-live', priority);
    liveRegion.setAttribute('aria-atomic', 'true');
    liveRegion.className = 'sr-only';
    liveRegion.textContent = message;

    document.body.appendChild(liveRegion);

    setTimeout(() => {
      document.body.removeChild(liveRegion);
    }, 1000);
  };

  return { announceToScreenReader };
};