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
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ImageModal from './ImageModal';
import ProblemImageList from './ProblemImageList';
import { Problem } from '../services/types';
import { pickImageUrls } from '../utils/problemImages';

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

  // 画像URL（新方式優先、旧方式フォールバック）
  const questionImages = pickImageUrls(problem.question_images, problem.question_image);
  const explanationImages = pickImageUrls(problem.explanation_images, problem.explanation_image);

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
      <ProblemImageList images={questionImages} alt="問題画像" onImageClick={setImageModalOpen} />

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
          <ProblemImageList images={explanationImages} alt="解説画像" onImageClick={setImageModalOpen} />
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
