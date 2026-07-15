/**
 * 問題プレビューコンポーネント
 * イシュー#033対応
 *
 * 機能:
 * - 問題文・選択肢・解説のテキスト表示
 * - 問題画像・解説画像の表示（複数対応）
 * - 画像クリックで拡大表示
 *
 * 使用箇所:
 * - QuizManagement.tsx（問題プレビューダイアログ）
 * - 将来: 確認画面、登録結果画面等
 */
import React, { useState } from 'react';
import {
  Box,
  Typography,
  Chip,
  Divider,
  ImageList,
  ImageListItem,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ImageModal from './ImageModal';
import { Problem } from '../services/types';
import { getMediaUrl } from '../utils/url';

interface ProblemPreviewProps {
  problem: Problem;
  showCorrectAnswer?: boolean;
  showExplanation?: boolean;
}

const ProblemPreview: React.FC<ProblemPreviewProps> = ({
  problem,
  showCorrectAnswer = true,
  showExplanation = true,
}) => {
  const [imageModalOpen, setImageModalOpen] = useState<string>('');

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return 'success';
      case 'medium': return 'warning';
      case 'hard': return 'error';
      default: return 'default';
    }
  };

  const getDifficultyLabel = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return '初級';
      case 'medium': return '中級';
      case 'hard': return '上級';
      default: return difficulty;
    }
  };

  const getProblemTypeLabel = (type: string) => {
    switch (type) {
      case 'single_choice': return '単一選択';
      case 'multiple_choice': return '複数選択';
      default: return type;
    }
  };

  // 画像URLを取得（新方式優先、旧方式フォールバック）
  const getQuestionImageUrls = (): string[] => {
    if (problem.question_images && problem.question_images.length > 0) {
      return problem.question_images.map(asset => asset.url);
    }
    if (problem.question_image) {
      return [problem.question_image];
    }
    return [];
  };

  const getExplanationImageUrls = (): string[] => {
    if (problem.explanation_images && problem.explanation_images.length > 0) {
      return problem.explanation_images.map(asset => asset.url);
    }
    if (problem.explanation_image) {
      return [problem.explanation_image];
    }
    return [];
  };

  const questionImages = getQuestionImageUrls();
  const explanationImages = getExplanationImageUrls();

  // 画像表示コンポーネント（アクセシビリティ対応）
  const renderImages = (images: string[], alt: string) => {
    if (images.length === 0) return null;

    return (
      <Box sx={{ mt: 2 }}>
        <ImageList cols={images.length === 1 ? 1 : Math.min(images.length, 3)} gap={8}>
          {images.map((imageUrl, index) => (
            <ImageListItem key={index}>
              <Box
                component="img"
                src={getMediaUrl(imageUrl)}
                alt={`${alt} ${index + 1}`}
                role="button"
                tabIndex={0}
                aria-label={`${alt} ${index + 1}枚目。クリックで拡大表示`}
                loading="lazy"
                sx={{
                  width: '100%',
                  maxHeight: 300,
                  objectFit: 'contain',
                  borderRadius: 1,
                  cursor: 'pointer',
                  border: '1px solid',
                  borderColor: 'divider',
                  '&:hover': {
                    opacity: 0.9,
                  },
                  '&:focus': {
                    outline: '2px solid',
                    outlineColor: 'primary.main',
                    outlineOffset: 2,
                  },
                }}
                onClick={() => setImageModalOpen(getMediaUrl(imageUrl))}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setImageModalOpen(getMediaUrl(imageUrl));
                  }
                }}
              />
            </ImageListItem>
          ))}
        </ImageList>
      </Box>
    );
  };

  return (
    <Box>
      {/* メタ情報（科目・難易度・問題タイプ） */}
      <Box sx={{ mb: 2 }}>
        {problem.subject_name && (
          <Chip label={problem.subject_name} sx={{ mr: 1 }} />
        )}
        <Chip
          label={getDifficultyLabel(problem.difficulty)}
          color={getDifficultyColor(problem.difficulty) as any}
          sx={{ mr: 1 }}
        />
        <Chip
          label={getProblemTypeLabel(problem.problem_type)}
          variant="outlined"
        />
      </Box>

      {/* 問題文 */}
      <Typography variant="h6" sx={{ mb: 2 }}>
        {problem.question_text}
      </Typography>

      {/* 問題画像 */}
      {renderImages(questionImages, '問題画像')}

      {/* 選択肢 */}
      <Box sx={{ my: 2 }}>
        {problem.choices.map((choice, index) => (
          <Box
            key={choice.id || index}
            sx={{
              p: 1,
              mb: 1,
              border: 1,
              borderColor: showCorrectAnswer && choice.is_correct ? 'success.main' : 'grey.300',
              borderRadius: 1,
              backgroundColor: showCorrectAnswer && choice.is_correct ? 'success.light' : 'transparent',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <Typography>
              {String.fromCharCode(65 + index)}. {choice.text}
            </Typography>
            {showCorrectAnswer && choice.is_correct && (
              <Chip icon={<CheckCircleIcon />} label="正解" size="small" color="success" />
            )}
          </Box>
        ))}
      </Box>

      {/* 解説 */}
      {showExplanation && problem.explanation && (
        <Box>
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2" gutterBottom>
            解説:
          </Typography>
          <Typography variant="body2">
            {problem.explanation}
          </Typography>

          {/* 解説画像 */}
          {renderImages(explanationImages, '解説画像')}
        </Box>
      )}

      {/* 画像拡大モーダル */}
      <ImageModal
        imageUrl={imageModalOpen}
        open={!!imageModalOpen}
        onClose={() => setImageModalOpen('')}
      />
    </Box>
  );
};

export default ProblemPreview;
