import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Box, IconButton, Tooltip, Fab, Typography, Slider, FormControlLabel, Switch } from '@mui/material';
import {
  Accessibility as AccessibilityIcon,
  TextIncrease as TextIncreaseIcon,
  TextDecrease as TextDecreaseIcon,
  Contrast as ContrastIcon,
  VolumeUp as VolumeUpIcon,
  Keyboard as KeyboardIcon,
  Visibility as VisibilityIcon
} from '@mui/icons-material';

interface AccessibilitySettings {
  fontSize: number;
  highContrast: boolean;
  screenReader: boolean;
  keyboardNavigation: boolean;
  reducedMotion: boolean;
  voiceAnnouncements: boolean;
  focusVisible: boolean;
}

interface AccessibilityContextType {
  settings: AccessibilitySettings;
  updateSetting: <K extends keyof AccessibilitySettings>(key: K, value: AccessibilitySettings[K]) => void;
  speak: (text: string) => void;
  isAccessibilityPanelOpen: boolean;
  toggleAccessibilityPanel: () => void;
}

const defaultSettings: AccessibilitySettings = {
  fontSize: 16,
  highContrast: false,
  screenReader: false,
  keyboardNavigation: true,
  reducedMotion: false,
  voiceAnnouncements: false,
  focusVisible: true
};

const AccessibilityContext = createContext<AccessibilityContextType | undefined>(undefined);

interface AccessibilityProviderProps {
  children: ReactNode;
}

export const AccessibilityProvider: React.FC<AccessibilityProviderProps> = ({ children }) => {
  const [settings, setSettings] = useState<AccessibilitySettings>(() => {
    // ローカルストレージから設定を復元
    const saved = localStorage.getItem('accessibility-settings');
    return saved ? { ...defaultSettings, ...JSON.parse(saved) } : defaultSettings;
  });
  
  const [isAccessibilityPanelOpen, setIsAccessibilityPanelOpen] = useState(false);
  const [speechSynthesis, setSpeechSynthesis] = useState<SpeechSynthesis | null>(null);

  useEffect(() => {
    // Web Speech API の初期化
    if ('speechSynthesis' in window) {
      setSpeechSynthesis(window.speechSynthesis);
    }

    // キーボードナビゲーションの設定
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!settings.keyboardNavigation) return;

      // Alt + A でアクセシビリティパネルを開く
      if (event.altKey && event.key === 'a') {
        event.preventDefault();
        setIsAccessibilityPanelOpen(prev => !prev);
      }

      // Esc でアクセシビリティパネルを閉じる
      if (event.key === 'Escape' && isAccessibilityPanelOpen) {
        setIsAccessibilityPanelOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [settings.keyboardNavigation, isAccessibilityPanelOpen]);

  useEffect(() => {
    // 設定をローカルストレージに保存
    localStorage.setItem('accessibility-settings', JSON.stringify(settings));

    // CSS変数を更新
    const root = document.documentElement;
    root.style.setProperty('--accessibility-font-size', `${settings.fontSize}px`);
    
    // ハイコントラストモード
    if (settings.highContrast) {
      root.classList.add('high-contrast');
    } else {
      root.classList.remove('high-contrast');
    }

    // モーション削減
    if (settings.reducedMotion) {
      root.classList.add('reduced-motion');
    } else {
      root.classList.remove('reduced-motion');
    }

    // フォーカス表示
    if (settings.focusVisible) {
      root.classList.add('focus-visible');
    } else {
      root.classList.remove('focus-visible');
    }

  }, [settings]);

  const updateSetting = <K extends keyof AccessibilitySettings>(
    key: K, 
    value: AccessibilitySettings[K]
  ) => {
    // eslint-disable-next-line security/detect-object-injection
    setSettings(prev => ({ ...prev, [key]: value }));
    
    // 変更時のアナウンス
    if (settings.voiceAnnouncements) {
      speak(`設定が変更されました: ${key}`);
    }
  };

  const speak = (text: string) => {
    if (!speechSynthesis || !settings.voiceAnnouncements) return;
    
    // 既存の発話を停止
    speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'ja-JP';
    utterance.rate = 0.8;
    utterance.pitch = 1;
    speechSynthesis.speak(utterance);
  };

  const toggleAccessibilityPanel = () => {
    setIsAccessibilityPanelOpen(prev => !prev);
  };

  const contextValue: AccessibilityContextType = {
    settings,
    updateSetting,
    speak,
    isAccessibilityPanelOpen,
    toggleAccessibilityPanel
  };

  return (
    <AccessibilityContext.Provider value={contextValue}>
      <div style={{ fontSize: settings.fontSize }}>
        {children}
      </div>
      
      {/* アクセシビリティコントロールパネル */}
      <AccessibilityPanel />
      
      {/* アクセシビリティFAB */}
      <Tooltip title="アクセシビリティ設定 (Alt+A)">
        <Fab
          size="medium"
          color="secondary"
          aria-label="アクセシビリティ設定"
          sx={{
            position: 'fixed',
            bottom: 80,
            right: 16,
            zIndex: 1000
          }}
          onClick={toggleAccessibilityPanel}
        >
          <AccessibilityIcon />
        </Fab>
      </Tooltip>
    </AccessibilityContext.Provider>
  );
};

const AccessibilityPanel: React.FC = () => {
  const context = useContext(AccessibilityContext);
  if (!context) return null;

  const { settings, updateSetting, isAccessibilityPanelOpen, speak } = context;

  if (!isAccessibilityPanelOpen) return null;

  const handleFontSizeChange = (increment: boolean) => {
    const newSize = increment 
      ? Math.min(settings.fontSize + 2, 24)
      : Math.max(settings.fontSize - 2, 12);
    updateSetting('fontSize', newSize);
  };

  return (
    <Box
      sx={{
        position: 'fixed',
        bottom: 140,
        right: 16,
        width: 320,
        maxHeight: 500,
        bgcolor: 'background.paper',
        boxShadow: 3,
        borderRadius: 2,
        p: 2,
        zIndex: 1001,
        border: '2px solid',
        borderColor: 'primary.main'
      }}
      role="dialog"
      aria-label="アクセシビリティ設定パネル"
    >
      <Typography variant="h6" gutterBottom>
        アクセシビリティ設定
      </Typography>

      {/* フォントサイズ */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          フォントサイズ: {settings.fontSize}px
        </Typography>
        <Box display="flex" alignItems="center" gap={1}>
          <IconButton
            onClick={() => handleFontSizeChange(false)}
            disabled={settings.fontSize <= 12}
            aria-label="フォントサイズを小さく"
          >
            <TextDecreaseIcon />
          </IconButton>
          <Slider
            value={settings.fontSize}
            onChange={(_, value) => updateSetting('fontSize', value as number)}
            min={12}
            max={24}
            step={2}
            sx={{ flex: 1 }}
            aria-label="フォントサイズ"
          />
          <IconButton
            onClick={() => handleFontSizeChange(true)}
            disabled={settings.fontSize >= 24}
            aria-label="フォントサイズを大きく"
          >
            <TextIncreaseIcon />
          </IconButton>
        </Box>
      </Box>

      {/* ハイコントラスト */}
      <FormControlLabel
        control={
          <Switch
            checked={settings.highContrast}
            onChange={(e) => updateSetting('highContrast', e.target.checked)}
          />
        }
        label={
          <Box display="flex" alignItems="center" gap={1}>
            <ContrastIcon />
            <Typography>ハイコントラスト</Typography>
          </Box>
        }
        sx={{ mb: 1 }}
      />

      {/* 音声アナウンス */}
      <FormControlLabel
        control={
          <Switch
            checked={settings.voiceAnnouncements}
            onChange={(e) => {
              const checked = e.target.checked;
              updateSetting('voiceAnnouncements', checked);
              if (checked) {
                speak('音声アナウンスが有効になりました');
              }
            }}
          />
        }
        label={
          <Box display="flex" alignItems="center" gap={1}>
            <VolumeUpIcon />
            <Typography>音声アナウンス</Typography>
          </Box>
        }
        sx={{ mb: 1 }}
      />

      {/* キーボードナビゲーション */}
      <FormControlLabel
        control={
          <Switch
            checked={settings.keyboardNavigation}
            onChange={(e) => updateSetting('keyboardNavigation', e.target.checked)}
          />
        }
        label={
          <Box display="flex" alignItems="center" gap={1}>
            <KeyboardIcon />
            <Typography>キーボードナビゲーション</Typography>
          </Box>
        }
        sx={{ mb: 1 }}
      />

      {/* モーション削減 */}
      <FormControlLabel
        control={
          <Switch
            checked={settings.reducedMotion}
            onChange={(e) => updateSetting('reducedMotion', e.target.checked)}
          />
        }
        label={
          <Box display="flex" alignItems="center" gap={1}>
            <VisibilityIcon />
            <Typography>モーション削減</Typography>
          </Box>
        }
        sx={{ mb: 1 }}
      />

      {/* フォーカス表示 */}
      <FormControlLabel
        control={
          <Switch
            checked={settings.focusVisible}
            onChange={(e) => updateSetting('focusVisible', e.target.checked)}
          />
        }
        label={
          <Typography>フォーカス枠を強調表示</Typography>
        }
        sx={{ mb: 2 }}
      />

      <Typography variant="caption" color="text.secondary">
        ショートカット: Alt+A でパネル開閉
      </Typography>
    </Box>
  );
};

export const useAccessibility = (): AccessibilityContextType => {
  const context = useContext(AccessibilityContext);
  if (context === undefined) {
    throw new Error('useAccessibility must be used within an AccessibilityProvider');
  }
  return context;
};

export default AccessibilityProvider;