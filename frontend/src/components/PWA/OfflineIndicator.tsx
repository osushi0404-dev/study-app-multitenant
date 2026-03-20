import React, { useState, useEffect } from 'react';
import {
  Snackbar,
  Alert,
  Box,
  Typography,
  Chip,
  Fade
} from '@mui/material';
import {
  WifiOff as OfflineIcon,
  Wifi as OnlineIcon,
  CloudOff as CloudOffIcon
} from '@mui/icons-material';
import pwaService from '../../services/pwa.service';

const OfflineIndicator: React.FC = () => {
  const [isOnline, setIsOnline] = useState(pwaService.getOnlineStatus());
  const [showMessage, setShowMessage] = useState(false);
  const [lastOnlineStatus, setLastOnlineStatus] = useState(isOnline);

  useEffect(() => {
    const unsubscribe = pwaService.onOnlineStatusChange((online) => {
      setIsOnline(online);
      
      // 状態が変わった時のみメッセージを表示
      if (online !== lastOnlineStatus) {
        setShowMessage(true);
        setLastOnlineStatus(online);
        
        // オンラインに戻った場合は短時間で非表示
        if (online) {
          setTimeout(() => setShowMessage(false), 2000);
        }
      }
    });

    return unsubscribe;
  }, [lastOnlineStatus]);

  const handleCloseMessage = () => {
    setShowMessage(false);
  };

  return (
    <>
      {/* 常時表示のオフラインインジケーター */}
      <Fade in={!isOnline}>
        <Box
          sx={{
            position: 'fixed',
            top: 64, // AppBar の下
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 1200,
            pointerEvents: 'none'
          }}
        >
          <Chip
            icon={<CloudOffIcon />}
            label="オフライン"
            color="warning"
            variant="filled"
            size="small"
            sx={{ 
              boxShadow: 2,
              pointerEvents: 'auto'
            }}
          />
        </Box>
      </Fade>

      {/* 状態変更時のメッセージ */}
      <Snackbar
        open={showMessage}
        autoHideDuration={isOnline ? 2000 : null} // オフライン時は手動で閉じるまで表示
        onClose={handleCloseMessage}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={handleCloseMessage}
          severity={isOnline ? 'success' : 'warning'}
          variant="filled"
          icon={isOnline ? <OnlineIcon /> : <OfflineIcon />}
          sx={{ minWidth: 300 }}
        >
          <Typography variant="body2" component="div">
            <strong>
              {isOnline ? 'オンラインに復帰しました' : 'オフライン状態です'}
            </strong>
          </Typography>
          <Typography variant="caption" component="div" sx={{ mt: 0.5 }}>
            {isOnline 
              ? '全ての機能が利用できます'
              : 'キャッシュされたデータのみ利用できます'
            }
          </Typography>
        </Alert>
      </Snackbar>
    </>
  );
};

export default OfflineIndicator;