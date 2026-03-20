import apiClient from '../services/api';

// 単一のバリデーションAPIを使用
export const validateField = async (
  fieldName: string,
  value: string
): Promise<{valid: boolean, message?: string}> => {
  try {
    const response = await apiClient.post('/api/auth/validate-field/', {
      field: fieldName,
      value: value
    });
    return response.data;
  } catch (error) {
    console.error('Validation error:', error);
    // エラー時は通過させ、送信時に再チェック
    return { valid: true };
  }
};

// メール・ユーザーIDチェックの便利関数
export const checkEmailAvailability = (email: string) =>
  validateField('email', email);

export const checkUserIdAvailability = (userId: string) =>
  validateField('user_id', userId);

export const checkPasswordStrength = (password: string) =>
  validateField('password', password);

// パスワード強度の視覚的フィードバック用
export const passwordStrengthCheck = (password: string): {
  strength: 'weak' | 'medium' | 'strong';
  requirements: {
    minLength: boolean;
    hasUpperCase: boolean;
    hasLowerCase: boolean;
    hasNumber: boolean;
    hasSpecialChar: boolean;
  };
} => {
  const requirements = {
    minLength: password.length >= 8,
    hasUpperCase: /[A-Z]/.test(password),
    hasLowerCase: /[a-z]/.test(password),
    hasNumber: /\d/.test(password),
    hasSpecialChar: /[!@#$%^&*]/.test(password)
  };

  // 強度判定
  const metRequirements = Object.values(requirements).filter(Boolean).length;
  let strength: 'weak' | 'medium' | 'strong' = 'weak';

  if (metRequirements >= 4) {
    strength = 'strong';
  } else if (metRequirements >= 3) {
    strength = 'medium';
  }

  return { strength, requirements };
};