import React, { useState, useEffect } from 'react';
import {
  Snackbar,
  Alert,
  Button,
  Typography,
  Box
} from '@mui/material';
import {
  SystemUpdate as UpdateIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import pwaService from '../../services/pwa.service';

const UpdateNotifier: React.FC = () => {
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    const unsubscribe = pwaService.onUpdate(() => {
      setUpdateAvailable(true);
    });

    return unsubscribe;
  }, []);

  const handleUpdate = async () => {
    setIsUpdating(true);
    
    try {
      const updated = await pwaService.updateServiceWorker();
      
      if (updated) {
        // ページをリロードして新しいバージョンを適用
        window.location.reload();
      }
    } catch (error) {
      console.error('Update failed:', error);
      setIsUpdating(false);
    }
  };

  const handleDismiss = () => {
    setUpdateAvailable(false);
  };

  if (!updateAvailable) {
    return null;
  }

  return (
    <Snackbar
      open={updateAvailable}
      anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      sx={{ top: { xs: 90, sm: 100 } }} // AppBar とオフラインインジケーターの下
    >
      <Alert
        severity="info"
        variant="filled"
        icon={<UpdateIcon />}
        action={
          <Box display="flex" gap={1}>
            <Button
              color="inherit"
              size="small"
              onClick={handleUpdate}
              disabled={isUpdating}
              startIcon={<RefreshIcon />}
            >
              {isUpdating ? '更新中...' : '更新'}
            </Button>
            <Button
              color="inherit"
              size="small"
              onClick={handleDismiss}
              disabled={isUpdating}
            >
              後で
            </Button>
          </Box>
        }
        sx={{ minWidth: 350 }}
      >
        <Typography variant="body2" component="div">
          <strong>新しいバージョンが利用可能です</strong>
        </Typography>
        <Typography variant="caption" component="div" sx={{ mt: 0.5 }}>
          最新の機能と改善を利用するために更新してください
        </Typography>
      </Alert>
    </Snackbar>
  );
};

export default UpdateNotifier;