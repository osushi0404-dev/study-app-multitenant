/**
 * 画像アップロードエリアコンポーネント
 * イシュー#031対応: 問題・解説画像のアップロード機能
 * イシュー#073対応: 既存画像（URL）と新規画像（File）の混在表示・並び替え・削除
 */
import React, { useState, useCallback } from 'react';
import {
  Box,
  Typography,
  IconButton,
  ImageList,
  ImageListItem,
  ImageListItemBar,
  Alert,
  Paper,
} from '@mui/material';
import {
  CloudUpload as CloudUploadIcon,
  Delete as DeleteIcon,
  Image as ImageIcon,
  ArrowUpward as ArrowUpwardIcon,
  ArrowDownward as ArrowDownwardIcon,
} from '@mui/icons-material';
import { EditableImage } from '../services/types';

interface ImageUploadAreaProps {
  /** 表示ラベル（例: "問題用画像", "解説用画像"） */
  label: string;
  /** 既存＋新規を1リストで表す画像アイテム */
  items: EditableImage[];
  /** 画像追加時のコールバック（新規Fileのみ） */
  onImagesAdd: (files: File[]) => void;
  /** 画像削除時のコールバック */
  onRemove: (index: number) => void;
  /** 上に移動 */
  onMoveUp: (index: number) => void;
  /** 下に移動 */
  onMoveDown: (index: number) => void;
  /** 最大アップロード枚数（デフォルト: 5） */
  maxImages?: number;
  /** 無効化フラグ */
  disabled?: boolean;
}

/**
 * 画像アップロードエリアコンポーネント
 *
 * 機能:
 * - ドラッグ&ドロップ／ファイル選択での新規画像追加
 * - 既存画像（サーバ保存済み・URL）と新規画像（未送信File）の混在プレビュー
 * - 上下ボタンによる並び替え（先頭の↑・末尾の↓は無効化）
 * - 個別の画像削除（保存するまでローカルのみ＝取り消し可能）
 * - クライアント側バリデーション（ファイル形式、サイズ、枚数）
 */
// 対応画像形式
const ALLOWED_FORMATS = ['image/png', 'image/jpeg', 'image/webp'];
const ALLOWED_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp'];

// ファイルサイズ制限（5MB）
const MAX_FILE_SIZE = 5 * 1024 * 1024;

const ImageUploadArea: React.FC<ImageUploadAreaProps> = ({
  label,
  items,
  onImagesAdd,
  onRemove,
  onMoveUp,
  onMoveDown,
  maxImages = 5,
  disabled = false,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  /**
   * ファイルのバリデーション（フロントエンド側）
   */
  const validateFiles = useCallback((files: File[]): { valid: File[]; errors: string[] } => {
    const valid: File[] = [];
    const errors: string[] = [];

    // 枚数チェック（既存＋新規の合計で判定）
    const remainingSlots = maxImages - items.length;
    if (files.length > remainingSlots) {
      errors.push(`画像は最大${maxImages}枚までアップロード可能です（残り${remainingSlots}枚）`);
      files = files.slice(0, Math.max(0, remainingSlots));
    }

    for (const file of files) {
      // ファイル形式チェック
      if (!ALLOWED_FORMATS.includes(file.type)) {
        errors.push(`${file.name}: 非対応の画像形式です（対応: PNG, JPEG, WebP）`);
        continue;
      }

      // ファイルサイズチェック
      if (file.size > MAX_FILE_SIZE) {
        const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
        errors.push(`${file.name}: ファイルサイズが大きすぎます（${sizeMB}MB、最大5MB）`);
        continue;
      }

      // ファイル名の基本チェック
      if (file.name.includes('..') || file.name.includes('/') || file.name.includes('\\')) {
        errors.push(`${file.name}: ファイル名に不正な文字が含まれています`);
        continue;
      }

      valid.push(file);
    }

    return { valid, errors };
  }, [items.length, maxImages]);

  /**
   * ファイル選択ハンドラー
   */
  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    const { valid, errors } = validateFiles(files);

    if (errors.length > 0) {
      setValidationError(errors.join('\n'));
    } else {
      setValidationError(null);
    }

    if (valid.length > 0) {
      onImagesAdd(valid);
    }

    // input要素をリセット（同じファイルを再選択可能にする）
    event.target.value = '';
  }, [validateFiles, onImagesAdd]);

  /**
   * ドラッグ開始ハンドラー
   */
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragging(true);
    }
  }, [disabled]);

  /**
   * ドラッグ終了ハンドラー
   */
  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  /**
   * ドラッグオーバーハンドラー
   */
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  /**
   * ドロップハンドラー
   */
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (disabled) return;

    const files = Array.from(e.dataTransfer.files);
    const { valid, errors } = validateFiles(files);

    if (errors.length > 0) {
      setValidationError(errors.join('\n'));
    } else {
      setValidationError(null);
    }

    if (valid.length > 0) {
      onImagesAdd(valid);
    }
  }, [disabled, validateFiles, onImagesAdd]);

  /**
   * 画像削除ハンドラー
   */
  const handleRemove = useCallback((index: number) => {
    onRemove(index);
    setValidationError(null);
  }, [onRemove]);

  /** プレビューURL・タイトル・サブタイトルをアイテム種別から導出 */
  const getPreview = (item: EditableImage) => {
    if (item.kind === 'existing') {
      return { src: item.url, title: item.filename, subtitle: '保存済み' };
    }
    return {
      src: URL.createObjectURL(item.file),
      title: item.file.name,
      subtitle: `${(item.file.size / 1024).toFixed(1)} KB`,
    };
  };

  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold' }}>
        {label}
      </Typography>

      <Typography variant="caption" display="block" sx={{ mb: 1, color: 'text.secondary' }}>
        最大{maxImages}枚まで登録可能 / 対応形式: PNG, JPEG, WebP / 最大5MB / 最大4096x4096ピクセル
      </Typography>

      {validationError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setValidationError(null)}>
          {validationError}
        </Alert>
      )}

      {/* ドラッグ&ドロップエリア */}
      {items.length < maxImages && (
        <Paper
          elevation={0}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          sx={{
            border: '2px dashed',
            borderColor: isDragging ? 'primary.main' : 'divider',
            backgroundColor: isDragging ? 'action.hover' : 'background.default',
            borderRadius: 2,
            p: 3,
            textAlign: 'center',
            cursor: disabled ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s',
            '&:hover': disabled ? {} : {
              borderColor: 'primary.main',
              backgroundColor: 'action.hover',
            },
          }}
        >
          <input
            type="file"
            accept={ALLOWED_EXTENSIONS.join(',')}
            multiple
            onChange={handleFileSelect}
            disabled={disabled}
            style={{ display: 'none' }}
            id={`${label}-file-input`}
          />

          <label htmlFor={`${label}-file-input`} style={{ cursor: disabled ? 'not-allowed' : 'pointer' }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
              <CloudUploadIcon sx={{ fontSize: 48, color: 'text.secondary' }} />
              <Typography variant="body2" color="text.secondary">
                画像をドラッグ&ドロップ、またはクリックして選択
              </Typography>
              <Typography variant="caption" color="text.secondary">
                残り{maxImages - items.length}枚
              </Typography>
            </Box>
          </label>
        </Paper>
      )}

      {/* 画像プレビュー（既存＋新規・並び替え可能） */}
      {items.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <ImageList cols={3} gap={8} sx={{ maxHeight: 400 }}>
            {items.map((item, index) => {
              const preview = getPreview(item);
              const itemKey = item.kind === 'existing' ? `existing-${item.assetId}` : `new-${index}-${item.file.name}`;
              return (
                <ImageListItem key={itemKey}>
                  <Box
                    component="img"
                    src={preview.src}
                    alt={preview.title}
                    loading="lazy"
                    sx={{
                      width: '100%',
                      height: 150,
                      objectFit: 'cover',
                      borderRadius: 1,
                    }}
                  />
                  <ImageListItemBar
                    title={preview.title}
                    subtitle={preview.subtitle}
                    actionIcon={
                      <Box sx={{ display: 'flex' }}>
                        <IconButton
                          sx={{ color: 'rgba(255, 255, 255, 0.8)' }}
                          aria-label="上に移動"
                          onClick={() => onMoveUp(index)}
                          disabled={disabled || index === 0}
                        >
                          <ArrowUpwardIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          sx={{ color: 'rgba(255, 255, 255, 0.8)' }}
                          aria-label="下に移動"
                          onClick={() => onMoveDown(index)}
                          disabled={disabled || index === items.length - 1}
                        >
                          <ArrowDownwardIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          sx={{ color: 'rgba(255, 255, 255, 0.8)' }}
                          aria-label="削除"
                          onClick={() => handleRemove(index)}
                          disabled={disabled}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    }
                    sx={{
                      background: 'linear-gradient(to top, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.3) 70%, rgba(0,0,0,0) 100%)',
                    }}
                  />
                </ImageListItem>
              );
            })}
          </ImageList>
        </Box>
      )}

      {/* 画像が最大枚数に達した場合のメッセージ */}
      {items.length >= maxImages && (
        <Alert severity="info" sx={{ mt: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <ImageIcon />
            <Typography variant="body2">
              最大{maxImages}枚に達しました。追加する場合は既存の画像を削除してください。
            </Typography>
          </Box>
        </Alert>
      )}
    </Box>
  );
};

export default ImageUploadArea;
