import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Box,
  Typography,
  CircularProgress,
  Alert,
  Stepper,
  Step,
  StepLabel,
  Card,
  CardContent,
  Chip,
  Switch,
  FormControlLabel
} from '@mui/material';
import {
  AutoAwesome as AIIcon,
  Psychology as AdaptiveIcon,
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import apiService from '../services/api';
import { Subject } from '../services/types';

interface AIQuestionGeneratorProps {
  open: boolean;
  onClose: () => void;
  subjects: Subject[];
  onProblemGenerated: () => void;
}

interface GenerationSettings {
  subject_id: number | '';
  difficulty: 'easy' | 'medium' | 'hard';
  problem_type: 'multiple_choice' | 'essay' | 'true_false';
  count: number;
  topic?: string;
  save_to_db: boolean;
  use_adaptive: boolean;
}

const difficultyLabels = {
  easy: '初級',
  medium: '中級',
  hard: '上級'
};

const problemTypeLabels = {
  multiple_choice: '選択問題',
  essay: '記述問題',
  true_false: '正誤判定'
};

const AIQuestionGenerator: React.FC<AIQuestionGeneratorProps> = ({
  open,
  onClose,
  subjects,
  onProblemGenerated
}) => {
  const [activeStep, setActiveStep] = useState(0);
  const [generating, setGenerating] = useState(false);
  const [settings, setSettings] = useState<GenerationSettings>({
    subject_id: '',
    difficulty: 'medium',
    problem_type: 'multiple_choice',
    count: 1,
    topic: '',
    save_to_db: true,
    use_adaptive: false
  });
  const [generatedProblems, setGeneratedProblems] = useState<any[]>([]);
  const [adaptationInfo, setAdaptationInfo] = useState<any>(null);

  const steps = ['設定', '生成', '確認'];

  const handleSettingChange = (field: keyof GenerationSettings, value: any) => {
    setSettings(prev => ({
      ...prev,
      // eslint-disable-next-line security/detect-object-injection
      [field]: value
    }));
  };

  const handleNext = () => {
    if (activeStep === 0) {
      // 設定検証
      if (!settings.subject_id) {
        toast.error('科目を選択してください');
        return;
      }
      setActiveStep(1);
      generateProblems();
    } else if (activeStep === 1) {
      setActiveStep(2);
    }
  };

  const handleBack = () => {
    setActiveStep(prev => prev - 1);
  };

  const generateProblems = async () => {
    setGenerating(true);
    setGeneratedProblems([]);
    setAdaptationInfo(null);

    try {
      let response;
      
      if (settings.use_adaptive) {
        // 適応的問題生成
        response = await apiService.post('/api/problems/generate_adaptive/', {
          subject_id: settings.subject_id
        });
        
        if (response.data.success) {
          setGeneratedProblems([response.data.problem]);
          setAdaptationInfo(response.data.adaptation_info);
        }
      } else {
        // 通常のAI問題生成
        response = await apiService.post('/api/problems/generate_ai/', {
          subject_id: settings.subject_id,
          difficulty: settings.difficulty,
          problem_type: settings.problem_type,
          count: settings.count,
          topic: settings.topic || undefined,
          save_to_db: settings.save_to_db
        });
        
        if (response.data.success) {
          if (settings.count === 1) {
            setGeneratedProblems([response.data.problem]);
          } else {
            setGeneratedProblems(response.data.problems);
          }
        }
      }
      
      toast.success('問題を生成しました');
      
    } catch (error: any) {
      console.error('AI問題生成エラー:', error);
      toast.error(error.response?.data?.error || 'AI問題生成に失敗しました');
    } finally {
      setGenerating(false);
    }
  };

  const handleFinish = () => {
    onProblemGenerated();
    handleClose();
  };

  const handleClose = () => {
    setActiveStep(0);
    setGenerating(false);
    setGeneratedProblems([]);
    setAdaptationInfo(null);
    setSettings({
      subject_id: '',
      difficulty: 'medium',
      problem_type: 'multiple_choice',
      count: 1,
      topic: '',
      save_to_db: true,
      use_adaptive: false
    });
    onClose();
  };

  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        return (
          <Box sx={{ minHeight: 400 }}>
            <Typography variant="h6" gutterBottom>
              AI問題生成設定
            </Typography>
            
            <Box sx={{ mb: 3 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.use_adaptive}
                    onChange={(e) => handleSettingChange('use_adaptive', e.target.checked)}
                  />
                }
                label={
                  <Box display="flex" alignItems="center" gap={1}>
                    <AdaptiveIcon />
                    <Typography>適応的生成（学習履歴に基づく個人最適化）</Typography>
                  </Box>
                }
              />
              {settings.use_adaptive && (
                <Alert severity="info" sx={{ mt: 1 }}>
                  あなたの学習履歴を分析して、最適な難易度とトピックの問題を生成します
                </Alert>
              )}
            </Box>

            <FormControl fullWidth margin="normal" required>
              <InputLabel>科目</InputLabel>
              <Select
                value={settings.subject_id}
                onChange={(e) => handleSettingChange('subject_id', e.target.value)}
              >
                {subjects.map((subject) => (
                  <MenuItem key={subject.id} value={subject.id}>
                    {subject.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {!settings.use_adaptive && (
              <>
                <FormControl fullWidth margin="normal">
                  <InputLabel>難易度</InputLabel>
                  <Select
                    value={settings.difficulty}
                    onChange={(e) => handleSettingChange('difficulty', e.target.value)}
                  >
                    {Object.entries(difficultyLabels).map(([key, label]) => (
                      <MenuItem key={key} value={key}>
                        {label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                <FormControl fullWidth margin="normal">
                  <InputLabel>問題形式</InputLabel>
                  <Select
                    value={settings.problem_type}
                    onChange={(e) => handleSettingChange('problem_type', e.target.value)}
                  >
                    {Object.entries(problemTypeLabels).map(([key, label]) => (
                      <MenuItem key={key} value={key}>
                        {label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                <TextField
                  fullWidth
                  margin="normal"
                  label="生成数"
                  type="number"
                  value={settings.count}
                  onChange={(e) => handleSettingChange('count', parseInt(e.target.value) || 1)}
                  inputProps={{ min: 1, max: 10 }}
                />

                <TextField
                  fullWidth
                  margin="normal"
                  label="特定トピック（オプション）"
                  value={settings.topic}
                  onChange={(e) => handleSettingChange('topic', e.target.value)}
                  helperText="特定のトピックに絞って問題を生成したい場合に入力"
                />
              </>
            )}

            <FormControlLabel
              control={
                <Switch
                  checked={settings.save_to_db}
                  onChange={(e) => handleSettingChange('save_to_db', e.target.checked)}
                />
              }
              label="データベースに保存"
              sx={{ mt: 2 }}
            />
          </Box>
        );

      case 1:
        return (
          <Box sx={{ minHeight: 400, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            {generating ? (
              <>
                <CircularProgress size={60} sx={{ mb: 3 }} />
                <Typography variant="h6" gutterBottom>
                  AI問題を生成中...
                </Typography>
                <Typography color="text.secondary" textAlign="center">
                  {settings.use_adaptive 
                    ? 'あなたの学習履歴を分析して最適な問題を作成しています'
                    : `${settings.count}個の問題を生成しています`
                  }
                </Typography>
              </>
            ) : (
              <>
                <Typography variant="h6" color="success.main" gutterBottom>
                  ✓ 問題生成完了
                </Typography>
                <Typography color="text.secondary">
                  {generatedProblems.length}個の問題が生成されました
                </Typography>
              </>
            )}
          </Box>
        );

      case 2:
        return (
          <Box sx={{ minHeight: 400 }}>
            <Typography variant="h6" gutterBottom>
              生成された問題
            </Typography>

            {adaptationInfo && (
              <Alert severity="info" sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  適応的生成情報
                </Typography>
                <Typography variant="body2">
                  あなたの正答率: {(adaptationInfo.user_accuracy * 100).toFixed(1)}%
                </Typography>
                <Typography variant="body2">
                  選択された難易度: {difficultyLabels[adaptationInfo.difficulty_selected as keyof typeof difficultyLabels]}
                </Typography>
                {adaptationInfo.weak_areas_targeted.length > 0 && (
                  <Typography variant="body2">
                    対象弱点領域: {adaptationInfo.weak_areas_targeted.join(', ')}
                  </Typography>
                )}
              </Alert>
            )}

            {generatedProblems.map((problem, index) => (
              <Card key={index} sx={{ mb: 2 }}>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={1} mb={2}>
                    <Chip 
                      label={difficultyLabels[problem.difficulty as keyof typeof difficultyLabels]} 
                      color="primary" 
                      size="small" 
                    />
                    <Chip 
                      label={problemTypeLabels[problem.problem_type as keyof typeof problemTypeLabels]} 
                      variant="outlined" 
                      size="small" 
                    />
                  </Box>
                  
                  <Typography variant="h6" gutterBottom>
                    {problem.title}
                  </Typography>
                  
                  <Typography variant="body1" paragraph>
                    {problem.description}
                  </Typography>

                  {problem.problem_type === 'multiple_choice' && problem.choices && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        選択肢:
                      </Typography>
                      {problem.choices.map((choice: any, choiceIndex: number) => (
                        <Typography 
                          key={choiceIndex} 
                          variant="body2" 
                          sx={{ 
                            color: choice.is_correct ? 'success.main' : 'text.secondary',
                            fontWeight: choice.is_correct ? 'bold' : 'normal'
                          }}
                        >
                          {String.fromCharCode(65 + choiceIndex)}. {choice.text}
                          {choice.is_correct && ' ✓'}
                        </Typography>
                      ))}
                    </Box>
                  )}

                  {problem.explanation && (
                    <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        解説:
                      </Typography>
                      <Typography variant="body2">
                        {problem.explanation}
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            ))}
          </Box>
        );

      default:
        return null;
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <AIIcon />
          AI問題生成
        </Box>
      </DialogTitle>
      
      <DialogContent>
        <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {renderStepContent()}
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose}>
          キャンセル
        </Button>
        
        {activeStep > 0 && (
          <Button onClick={handleBack} disabled={generating}>
            戻る
          </Button>
        )}
        
        {activeStep < steps.length - 1 ? (
          <Button 
            onClick={handleNext} 
            variant="contained"
            disabled={generating || (activeStep === 0 && !settings.subject_id)}
          >
            次へ
          </Button>
        ) : (
          <Button 
            onClick={handleFinish} 
            variant="contained"
            color="success"
          >
            完了
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default AIQuestionGenerator;