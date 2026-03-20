import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useParams } from 'react-router-dom';
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  CircularProgress,
  IconButton,
  InputAdornment,
  Alert,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Stepper,
  Step,
  StepLabel,
} from '@mui/material';
import { Visibility, VisibilityOff } from '@mui/icons-material';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import toast from 'react-hot-toast';
import apiClient from '../services/api';
import SubjectService from '../services/subjectService';
import { Subject } from '../services/types';
import {
  checkEmailAvailability,
  checkUserIdAvailability,
  passwordStrengthCheck
} from '../utils/validation';
import { PasswordStrengthIndicator } from '../components/PasswordStrengthIndicator';

import { useAuth } from '../contexts/AuthContext';

interface RegisterFormData {
  email: string;
  userId: string;
  password: string;
  confirmPassword: string;
  firstName?: string;
  lastName?: string;
}


const schema = yup.object({
  email: yup
    .string()
    .email('有効なメールアドレスを入力してください')
    .required('メールアドレスは必須です'),
  userId: yup
    .string()
    .min(3, 'ユーザーIDは3文字以上で入力してください')
    .max(30, 'ユーザーIDは30文字以内で入力してください')
    .matches(/^[a-zA-Z0-9_]+$/, 'ユーザーIDは半角英数字とアンダースコアのみ使用できます')
    .required('ユーザーIDは必須です'),
  password: yup
    .string()
    .min(8, 'パスワードは8文字以上で入力してください')
    .matches(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      'パスワードは大文字、小文字、数字を含む必要があります'
    )
    .required('パスワードは必須です'),
  confirmPassword: yup
    .string()
    .oneOf([yup.ref('password')], 'パスワードが一致しません')
    .required('パスワード確認は必須です'),
  firstName: yup.string(),
  lastName: yup.string(),
});

const Register: React.FC = () => {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const navigate = useNavigate();
  const { organizationSlug } = useParams<{ organizationSlug?: string }>();

  // ステップ管理
  const [currentStep, setCurrentStep] = useState<1 | 2>(1);
  const [basicInfo, setBasicInfo] = useState<RegisterFormData | null>(null);

  const [organizationName, setOrganizationName] = useState<string>('');
  // organizationSlugがある場合は初期状態を検証中にする
  const [isValidatingOrg, setIsValidatingOrg] = useState(!!organizationSlug);
  const [orgValidationError, setOrgValidationError] = useState<string | null>(null);
  const { register: registerUser } = useAuth();

  // 科目選択関連のstate
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubjects, setSelectedSubjects] = useState<number[]>([]);
  const [subjectsLoading, setSubjectsLoading] = useState(false);

  // リアルタイムバリデーション関連のstate
  const [emailChecking, setEmailChecking] = useState(false);
  const [userIdChecking, setUserIdChecking] = useState(false);
  const [passwordStrength, setPasswordStrength] = useState<ReturnType<typeof passwordStrengthCheck> | null>(null);


  // 組織slugの事前検証
  useEffect(() => {
    const validateOrganizationSlug = async () => {
      if (organizationSlug) {
        setIsValidatingOrg(true);
        try {
          const response = await apiClient.get(`/api/organizations/validate-slug/${organizationSlug}/`);
          if (response.data.valid) {
            setOrganizationName(response.data.organization_name || '');
            setOrgValidationError(null);
          } else {
            setOrgValidationError(`組織URL "${organizationSlug}" は無効です`);
          }
        } catch (error: any) {
          if (error.response?.status === 404) {
            setOrgValidationError(`組織URL "${organizationSlug}" は見つかりません`);
          } else {
            setOrgValidationError('組織の確認中にエラーが発生しました');
          }
        } finally {
          setIsValidatingOrg(false);
        }
      } else {
        // slugがない場合は個人利用として処理
        setIsValidatingOrg(false);
      }
    };
    validateOrganizationSlug();
  }, [organizationSlug]);

  // 組織検証成功後かつステップ2の場合のみ科目一覧を取得
  useEffect(() => {
    // デバッグログ（一時的）
    console.log('科目取得useEffect実行', {
      organizationSlug,
      isValidatingOrg,
      orgValidationError,
      currentStep,
      shouldFetch: currentStep === 2 && !isValidatingOrg && !orgValidationError
    });

    const fetchSubjects = async () => {
      // ステップ2でない場合は何もしない
      if (currentStep !== 2) {
        console.log('ステップ2でないため科目取得をスキップ');
        return;
      }

      // 組織検証中は何もしない
      if (isValidatingOrg) {
        console.log('組織検証中のため科目取得をスキップ');
        return;
      }

      // 組織検証エラーがある場合も何もしない
      if (orgValidationError) {
        console.log('組織検証エラーのため科目取得をスキップ');
        return;
      }

      // すでに科目が読み込まれている場合はスキップ（重複読み込み防止）
      if (subjects.length > 0) {
        console.log('科目が既に読み込まれているためスキップ');
        return;
      }

      // 組織検証完了（成功）または個人登録の場合に科目を取得
      console.log('科目取得を開始');

      const fetchedSubjects = await SubjectService.getSubjectsWithLoading(
        organizationSlug,
        setSubjectsLoading,
        (error) => toast.error(error)
      );

      console.log('科目取得成功:', fetchedSubjects);
      setSubjects(fetchedSubjects);
    };

    fetchSubjects();
  }, [organizationSlug, isValidatingOrg, orgValidationError, currentStep]);

  const {
    register,
    handleSubmit,
    setError,
    watch,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: yupResolver(schema),
  });

  // リアルタイムバリデーション関数
  const handleEmailBlur = async (e: React.FocusEvent<HTMLInputElement>) => {
    const email = e.target.value;
    if (email) {
      setEmailChecking(true);
      try {
        const result = await checkEmailAvailability(email);
        if (!result.valid) {
          setError('email', {
            type: 'manual',
            message: result.message || 'このメールアドレスは既に使用されています'
          });
        }
      } catch (error) {
        console.error('Email validation error:', error);
      } finally {
        setEmailChecking(false);
      }
    }
  };

  const handleUserIdBlur = async (e: React.FocusEvent<HTMLInputElement>) => {
    const userId = e.target.value;
    if (userId) {
      setUserIdChecking(true);
      try {
        const result = await checkUserIdAvailability(userId);
        if (!result.valid) {
          setError('userId', {
            type: 'manual',
            message: result.message || 'このユーザーIDは既に使用されています'
          });
        }
      } catch (error) {
        console.error('UserId validation error:', error);
      } finally {
        setUserIdChecking(false);
      }
    }
  };

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const password = e.target.value;
    if (password) {
      setPasswordStrength(passwordStrengthCheck(password));
    } else {
      setPasswordStrength(null);
    }
  };

  // ステップ1: 基本情報の送信
  const onSubmitStep1 = async (data: RegisterFormData) => {
    // 送信前に重複チェックを実行
    let hasError = false;

    // メールアドレスの重複チェック
    if (data.email) {
      setEmailChecking(true);
      const emailResult = await checkEmailAvailability(data.email);
      if (!emailResult.valid) {
        setError('email', {
          type: 'manual',
          message: emailResult.message || 'このメールアドレスは既に使用されています'
        });
        hasError = true;
      }
      setEmailChecking(false);
    }

    // ユーザーIDの重複チェック
    if (data.userId) {
      setUserIdChecking(true);
      const userIdResult = await checkUserIdAvailability(data.userId);
      if (!userIdResult.valid) {
        setError('userId', {
          type: 'manual',
          message: userIdResult.message || 'このユーザーIDは既に使用されています'
        });
        hasError = true;
      }
      setUserIdChecking(false);
    }

    // エラーがなければ次のステップへ
    if (!hasError) {
      setBasicInfo(data);
      setCurrentStep(2);
    }
  };

  // ステップ2: 最終送信
  const onSubmitFinal = async () => {
    if (!basicInfo) {
      toast.error('基本情報が入力されていません');
      setCurrentStep(1);
      return;
    }

    if (selectedSubjects.length === 0) {
      toast.error('科目を最低1つ選択してください');
      return;
    }

    setLoading(true);
    try {
      await registerUser(
        basicInfo.email,
        basicInfo.userId,
        basicInfo.password,
        basicInfo.firstName,
        basicInfo.lastName,
        organizationSlug,
        selectedSubjects
      );
      const message = organizationSlug
        ? `${organizationName}への登録が完了しました。メール認証を行ってからログインしてください。`
        : '登録が完了しました。メール認証を行ってからログインしてください。';
      setSuccessMessage(message);

      // 3秒後にログインページへリダイレクト
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (error: any) {
      // Error handling is now done in AuthContext
      console.error('Registration error:', error);
      console.log('Error response:', error.response?.data);
    } finally {
      setLoading(false);
    }
  };

  // ステップ間のナビゲーション
  const handleBack = () => {
    if (currentStep === 2) {
      setCurrentStep(1);
    }
  };

  // 離脱警告
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (currentStep === 2 || basicInfo !== null) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [currentStep, basicInfo]);

  // 組織検証中の表示
  if (isValidatingOrg) {
    return (
      <Container component="main" maxWidth="sm">
        <Box
          sx={{
            marginTop: 8,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <Paper
            elevation={3}
            sx={{
              padding: 4,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              width: '100%',
            }}
          >
            <CircularProgress size={40} sx={{ mb: 2 }} />
            <Typography variant="body1">組織情報を確認中...</Typography>
          </Paper>
        </Box>
      </Container>
    );
  }

  // 組織検証エラーの表示（UX重視：同一ページ内でエラー表示）
  if (orgValidationError && organizationSlug) {
    return (
      <Container component="main" maxWidth="sm">
        <Box
          sx={{
            marginTop: 8,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <Paper
            elevation={3}
            sx={{
              padding: 4,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              width: '100%',
            }}
          >
            <Typography component="h1" variant="h5" color="error" gutterBottom>
              組織が見つかりません
            </Typography>
            
            <Box sx={{ mt: 2, mb: 3, width: '100%' }}>
              <Alert severity="error" sx={{ mb: 2 }}>
                {orgValidationError}
              </Alert>
              <Typography variant="body2" color="text.secondary" align="center">
                アクセスURL: /register/<strong>{organizationSlug}</strong>
              </Typography>
            </Box>

            <Box sx={{ width: '100%' }}>
              <Typography variant="h6" gutterBottom>
                次のアクションをお選びください：
              </Typography>
              
              <Button
                fullWidth
                variant="contained"
                color="primary"
                size="large"
                onClick={() => navigate('/register')}
                sx={{ mb: 2 }}
              >
                個人アカウントとして登録
              </Button>
              
              <Button
                fullWidth
                variant="outlined"
                color="secondary"
                size="large"
                onClick={() => window.history.back()}
                sx={{ mb: 3 }}
              >
                前のページに戻る
              </Button>
              
              <Box sx={{ p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
                <Typography variant="body2" color="text.secondary" paragraph>
                  組織URLが正しいか確認してください。
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  組織管理者から正しいURLを入手してください。
                </Typography>
              </Box>
            </Box>
          </Paper>
        </Box>
      </Container>
    );
  }

  if (successMessage) {
    return (
      <Container component="main" maxWidth="sm">
        <Box
          sx={{
            marginTop: 8,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <Paper
            elevation={3}
            sx={{
              padding: 4,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              width: '100%',
            }}
          >
            <Alert severity="success" sx={{ mb: 2, width: '100%' }}>
              {successMessage}
            </Alert>
            <Typography variant="body1" align="center">
              ログインページに自動的に移動します...
            </Typography>
          </Paper>
        </Box>
      </Container>
    );
  }

  // 科目選択セクション
  const renderSubjectSelection = () => (
    <Box sx={{ mt: 3, mb: 2 }}>
      <Typography variant="h6" gutterBottom>
        学習科目を選択してください（必須）
      </Typography>

      {subjectsLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
          <CircularProgress />
        </Box>
      ) : subjects.length === 0 ? (
        <Alert severity="warning" sx={{ mt: 2 }}>
          この組織には利用可能な科目がありません。管理者にお問い合わせください。
        </Alert>
      ) : (
        <FormGroup>
          {subjects.map((subject) => (
            <FormControlLabel
              key={subject.id}
              control={
                <Checkbox
                  checked={selectedSubjects.includes(subject.id)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedSubjects([...selectedSubjects, subject.id]);
                    } else {
                      setSelectedSubjects(
                        selectedSubjects.filter(id => id !== subject.id)
                      );
                    }
                  }}
                />
              }
              label={
                <Box>
                  <Typography variant="body1">{subject.name}</Typography>
                  {subject.description && (
                    <Typography variant="body2" color="text.secondary">
                      {subject.description}
                    </Typography>
                  )}
                </Box>
              }
            />
          ))}
        </FormGroup>
      )}

      {selectedSubjects.length === 0 && subjects.length > 0 && (
        <Typography variant="body2" color="error" sx={{ mt: 1 }}>
          ※ 最低1つの科目を選択してください
        </Typography>
      )}
    </Box>
  );

  return (
    <Container component="main" maxWidth="sm">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper
          elevation={3}
          sx={{
            padding: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            width: '100%',
          }}
        >
          <Typography component="h1" variant="h4" gutterBottom>
            学習アプリ
          </Typography>

          <Typography component="h2" variant="h5" gutterBottom>
            新規登録
          </Typography>

          {organizationSlug && organizationName && (
            <Alert severity="info" sx={{ mt: 1, mb: 2, width: '100%' }}>
              <strong>{organizationName}</strong>への登録
            </Alert>
          )}

          {/* ステップインジケーター */}
          <Stepper activeStep={currentStep - 1} sx={{ width: '100%', mb: 3 }}>
            <Step>
              <StepLabel>基本情報入力</StepLabel>
            </Step>
            <Step>
              <StepLabel>科目選択</StepLabel>
            </Step>
          </Stepper>

          {/* ステップ1: 基本情報入力 */}
          {currentStep === 1 && (
            <Box component="form" onSubmit={handleSubmit(onSubmitStep1)} sx={{ mt: 1, width: '100%' }}>
              <TextField
                margin="normal"
                fullWidth
                label="メールアドレス"
                type="email"
                autoComplete="email"
                autoFocus
                error={!!errors.email}
                helperText={errors.email?.message || (emailChecking ? 'チェック中...' : '')}
                defaultValue={basicInfo?.email || ''}
                {...register('email', {
                  onBlur: handleEmailBlur
                })}
                InputProps={{
                  endAdornment: emailChecking ? (
                    <InputAdornment position="end">
                      <CircularProgress size={20} />
                    </InputAdornment>
                  ) : null,
                }}
              />

              <TextField
                margin="normal"
                fullWidth
                label="ユーザーID"
                autoComplete="username"
                error={!!errors.userId}
                helperText={errors.userId?.message || (userIdChecking ? 'チェック中...' : '半角英数字とアンダースコアのみ')}
                inputProps={{
                  pattern: '[a-zA-Z0-9_]+'
                }}
                defaultValue={basicInfo?.userId || ''}
                {...register('userId', {
                  onBlur: handleUserIdBlur
                })}
                InputProps={{
                  endAdornment: userIdChecking ? (
                    <InputAdornment position="end">
                      <CircularProgress size={20} />
                    </InputAdornment>
                  ) : null,
                }}
              />

              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  margin="normal"
                  fullWidth
                  label="姓（任意）"
                  autoComplete="family-name"
                  error={!!errors.lastName}
                  helperText={errors.lastName?.message}
                  defaultValue={basicInfo?.lastName || ''}
                  {...register('lastName')}
                />
                <TextField
                  margin="normal"
                  fullWidth
                  label="名（任意）"
                  autoComplete="given-name"
                  error={!!errors.firstName}
                  helperText={errors.firstName?.message}
                  defaultValue={basicInfo?.firstName || ''}
                  {...register('firstName')}
                />
              </Box>

              <TextField
                margin="normal"
                fullWidth
                label="パスワード"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                error={!!errors.password}
                helperText={errors.password?.message}
                defaultValue={basicInfo?.password || ''}
                {...register('password', {
                  onChange: handlePasswordChange,
                })}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label="toggle password visibility"
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
              <PasswordStrengthIndicator strength={passwordStrength} />

              <TextField
                margin="normal"
                fullWidth
                label="パスワード確認"
                type={showConfirmPassword ? 'text' : 'password'}
                autoComplete="new-password"
                error={!!errors.confirmPassword}
                helperText={errors.confirmPassword?.message}
                defaultValue={basicInfo?.confirmPassword || ''}
                {...register('confirmPassword')}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label="toggle confirm password visibility"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        edge="end"
                      >
                        {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2 }}
              >
                登録して次へ
              </Button>

              <Box sx={{ textAlign: 'center' }}>
                <Link to="/login" style={{ textDecoration: 'none' }}>
                  <Typography variant="body2" color="primary">
                    すでにアカウントをお持ちの方はこちら
                  </Typography>
                </Link>
              </Box>
            </Box>
          )}

          {/* ステップ2: 科目選択 */}
          {currentStep === 2 && (
            <Box sx={{ width: '100%' }}>
              <Typography variant="h6" gutterBottom>
                ようこそ！学習したい科目を選択してください
              </Typography>

              {organizationName && (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {organizationName}で利用可能な科目一覧
                </Typography>
              )}

              {/* 科目選択セクション */}
              {renderSubjectSelection()}

              <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
                <Button
                  variant="outlined"
                  onClick={handleBack}
                  sx={{ flex: 1 }}
                >
                  戻る
                </Button>
                <Button
                  variant="contained"
                  onClick={onSubmitFinal}
                  disabled={loading || selectedSubjects.length === 0}
                  sx={{ flex: 1 }}
                >
                  {loading ? <CircularProgress size={24} /> : '登録を完了'}
                </Button>
              </Box>
            </Box>
          )}
        </Paper>
      </Box>
    </Container>
  );
};

export default Register;