/**
 * おすすめ練習問題（全科目）（I487。中身は I473 のまま）
 * 間違いやすい分野の科目の「練習する」は苦手を優先で始める（I466）
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Button, Card, CardContent, Typography } from '@mui/material';
import { DashboardOverview } from '../../types/api';
import { quizPath } from '../../constants/routes';

interface RecommendationsCardProps {
  recommendations: DashboardOverview['recommendations'];
}

const RecommendationsCard: React.FC<RecommendationsCardProps> = ({ recommendations }) => {
  const navigate = useNavigate();

  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Typography variant="h6" component="h2" gutterBottom>
          おすすめ練習問題（全科目）
        </Typography>
        {recommendations.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            現在、おすすめの練習問題はありません
          </Typography>
        ) : (
          recommendations.map((rec) => (
            <Box key={`${rec.kind}-${rec.subject_id}`} sx={{ mb: 2 }}>
              <Typography variant="body1">{rec.subject_name}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                {rec.reason}
              </Typography>
              <Button size="small" variant="text" onClick={() => navigate(quizPath(rec.subject_id, rec.kind === 'weak_subject' ? 'weak' : 'normal'))}>
                練習する
              </Button>
            </Box>
          ))
        )}
      </CardContent>
    </Card>
  );
};

export default RecommendationsCard;
