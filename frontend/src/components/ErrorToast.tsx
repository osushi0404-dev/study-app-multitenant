import React from 'react';
import { toast } from 'react-hot-toast';

interface ErrorData {
  error?: {
    main_message?: string;
    sub_message?: string;
    details?: any;
  };
}

export const showErrorToast = (error: any) => {
  // エラーレスポンスの構造を確認
  console.log('showErrorToast called with:', error);
  console.log('error.response:', error?.response);
  console.log('error.response.data:', error?.response?.data);
  
  const errorData = error?.response?.data as ErrorData;
  
  if (errorData?.error) {
    // 新しいエラー形式の場合
    const mainMessage = errorData.error.main_message || 'エラーが発生しました';
    const subMessage = errorData.error.sub_message;
    
    toast.error((t) => (
      <div style={{ maxWidth: '300px' }}>
        <div style={{ fontWeight: 'bold', marginBottom: subMessage ? '4px' : '0' }}>
          {mainMessage}
        </div>
        {subMessage && (
          <div style={{ fontSize: '0.875rem', opacity: 0.9 }}>
            {subMessage}
          </div>
        )}
      </div>
    ), {
      duration: 5000,
      style: {
        padding: '12px',
        minWidth: '250px',
      },
    });
  } else {
    // 従来のエラー形式の場合（フォールバック）
    const message = error?.response?.data?.detail || 
                   error?.response?.data?.message || 
                   error?.message ||
                   'エラーが発生しました';
    
    toast.error(message, {
      duration: 5000,
    });
  }
};

export const showSuccessToast = (message: string) => {
  toast.success(message, {
    duration: 4000,
  });
};

export const showWarningToast = (message: string) => {
  toast((t) => (
    <div style={{ display: 'flex', alignItems: 'center' }}>
      <span style={{ marginRight: '8px', fontSize: '1.2rem' }}>⚠️</span>
      <span>{message}</span>
    </div>
  ), {
    duration: 4000,
    style: {
      background: '#FFF3CD',
      color: '#856404',
      border: '1px solid #FFEAA7',
    },
  });
};