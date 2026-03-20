import React, { useState, useEffect } from 'react';
import {
  Button,
  Card,
  CardContent,
  CardActions,
  Typography,
  IconButton,
  Box,
  Snackbar,
  Alert
} from '@mui/material';
import {
  Close as CloseIcon,
  GetApp as InstallIcon,
  Smartphone as PhoneIcon
} from '@mui/icons-material';
import pwaService from '../../services/pwa.service';

interface InstallPromptProps {
  onClose?: () => void;
}

const InstallPrompt: React.FC<InstallPromptProps> = ({ onClose }) => {
  const [isVisible, setIsVisible] = useState(false);
  const [isInstalling, setIsInstalling] = useState(false);
  const [showSuccessMessage, setShowSuccessMessage] = useState(false);

  useEffect(() => {
    // アプリがすでにインストール済みまたはスタンドアロンの場合は表示しない
    if (pwaService.isStandalone()) {
      return;
    }

    // インストールプロンプトが利用可能かチェック
    const checkInstallPrompt = () => {
      if (pwaService.isInstallPromptAvailable()) {
        setIsVisible(true);
      }
    };

    checkInstallPrompt();

    // 少し遅延してもう一度チェック（プロンプトイベントが遅れる場合がある）
    const timer = setTimeout(checkInstallPrompt, 2000);

    return () => clearTimeout(timer);
  }, []);

  const handleInstall = async () => {
    setIsInstalling(true);
    
    try {
      const installed = await pwaService.showInstallPrompt();
      
      if (installed) {
        setShowSuccessMessage(true);
        setIsVisible(false);
        onClose?.();
      }
    } catch (error) {
      console.error('Install failed:', error);
    } finally {
      setIsInstalling(false);
    }
  };

  const handleClose = () => {
    setIsVisible(false);
    onClose?.();
  };

  if (!isVisible) {
    return null;
  }

  return (
    <>
      <Card 
        sx={{ 
          position: 'fixed',
          bottom: 16,
          left: 16,
          right: 16,
          zIndex: 1300,
          maxWidth: 400,
          margin: '0 auto',
          boxShadow: 3
        }}
      >
        <CardContent sx={{ pb: 1 }}>
          <Box display="flex" alignItems="flex-start" justifyContent="space-between">
            <Box display="flex" alignItems="center" gap={1} flex={1}>
              <PhoneIcon color="primary" />
              <Box>
                <Typography variant="h6" component="h3" gutterBottom>
                  アプリをインストール
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  ホーム画面に追加してより快適に学習しましょう
                </Typography>
              </Box>
            </Box>
            <IconButton 
              size="small" 
              onClick={handleClose}
              sx={{ mt: -0.5, mr: -0.5 }}
            >
              <CloseIcon />
            </IconButton>
          </Box>
        </CardContent>
        
        <CardActions sx={{ pt: 0, pb: 2, px: 2 }}>
          <Button
            variant="contained"
            startIcon={<InstallIcon />}
            onClick={handleInstall}
            disabled={isInstalling}
            fullWidth
          >
            {isInstalling ? 'インストール中...' : 'インストール'}
          </Button>
        </CardActions>
      </Card>

      <Snackbar
        open={showSuccessMessage}
        autoHideDuration={3000}
        onClose={() => setShowSuccessMessage(false)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert 
          onClose={() => setShowSuccessMessage(false)} 
          severity="success"
          variant="filled"
        >
          アプリが正常にインストールされました！
        </Alert>
      </Snackbar>
    </>
  );
};

export default InstallPrompt;