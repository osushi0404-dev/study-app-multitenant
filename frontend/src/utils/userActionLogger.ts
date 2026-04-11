/**
 * ユーザー操作をログに記録するユーティリティ
 * エラー発生時の原因特定のため、画面操作を追跡
 */

export interface UserAction {
  timestamp: string;
  actionType: 'click' | 'input' | 'navigation' | 'submit' | 'error';
  component: string;
  details: {
    elementId?: string;
    elementType?: string;
    value?: any;
    previousValue?: any;
    path?: string;
    errorMessage?: string;
    [key: string]: any;
  };
}

class UserActionLogger {
  private actions: UserAction[] = [];
  private maxActions = 50; // 最大50件の操作を保持

  /**
   * 操作をログに追加
   */
  log(action: Omit<UserAction, 'timestamp'>) {
    const timestampedAction: UserAction = {
      ...action,
      timestamp: new Date().toISOString(),
    };

    this.actions.push(timestampedAction);

    // 最大件数を超えたら古いものから削除
    if (this.actions.length > this.maxActions) {
      this.actions = this.actions.slice(-this.maxActions);
    }

    // セッションストレージにも保存（ページリロード対策）
    this.saveToSessionStorage();
  }

  /**
   * クリックイベントをログ
   */
  logClick(component: string, elementId?: string, details?: any) {
    this.log({
      actionType: 'click',
      component,
      details: {
        elementId,
        elementType: 'button',
        ...details,
      },
    });
  }

  /**
   * 入力イベントをログ
   */
  logInput(component: string, fieldName: string, value: any, previousValue?: any) {
    this.log({
      actionType: 'input',
      component,
      details: {
        elementId: fieldName,
        value: this.sanitizeValue(value),
        previousValue: this.sanitizeValue(previousValue),
      },
    });
  }

  /**
   * フォーム送信をログ
   */
  logSubmit(component: string, formData: any) {
    this.log({
      actionType: 'submit',
      component,
      details: {
        formData: this.sanitizeFormData(formData),
      },
    });
  }

  /**
   * ナビゲーションをログ
   */
  logNavigation(from: string, to: string) {
    this.log({
      actionType: 'navigation',
      component: 'Router',
      details: {
        from,
        to,
      },
    });
  }

  /**
   * エラーをログ
   */
  logError(component: string, error: any) {
    this.log({
      actionType: 'error',
      component,
      details: {
        errorMessage: error.message || String(error),
        errorType: error.name || 'Unknown',
      },
    });
  }

  /**
   * 直近のアクションを取得
   */
  getRecentActions(count: number = 10): UserAction[] {
    return this.actions.slice(-count);
  }

  /**
   * すべてのアクションを取得
   */
  getAllActions(): UserAction[] {
    return [...this.actions];
  }

  /**
   * APIリクエスト用にアクションを文字列化
   */
  getActionsForAPI(): string {
    return JSON.stringify(this.getRecentActions(20));
  }

  /**
   * アクションをクリア
   */
  clear() {
    this.actions = [];
    sessionStorage.removeItem('userActions');
  }

  /**
   * セッションストレージに保存
   */
  private saveToSessionStorage() {
    try {
      sessionStorage.setItem('userActions', JSON.stringify(this.actions));
    } catch (e) {
      console.error('Failed to save user actions to session storage:', e);
    }
  }

  /**
   * セッションストレージから復元
   */
  loadFromSessionStorage() {
    try {
      const stored = sessionStorage.getItem('userActions');
      if (stored) {
        this.actions = JSON.parse(stored);
      }
    } catch (e) {
      console.error('Failed to load user actions from session storage:', e);
    }
  }

  /**
   * センシティブな情報をサニタイズ
   */
  private sanitizeValue(value: any): any {
    if (typeof value === 'string') {
      // パスワードなどのセンシティブフィールドはマスク
      const sensitiveFields = ['password', 'token', 'secret', 'apiKey'];
      if (sensitiveFields.some(field => field.toLowerCase() === value.toLowerCase())) {
        return '[REDACTED]';
      }
    }
    return value;
  }

  /**
   * フォームデータをサニタイズ
   */
  private sanitizeFormData(formData: any): any {
    if (!formData || typeof formData !== 'object') {
      return formData;
    }

    const sanitized: any = {};
    const sensitiveFields = ['password', 'token', 'secret', 'apiKey', 'creditCard', 'cvv'];

    for (const [key, value] of Object.entries(formData)) {
      if (sensitiveFields.some(field => key.toLowerCase().includes(field.toLowerCase()))) {
        // eslint-disable-next-line security/detect-object-injection
        sanitized[key] = '[REDACTED]';
      } else {
        // eslint-disable-next-line security/detect-object-injection
        sanitized[key] = value;
      }
    }

    return sanitized;
  }
}

// シングルトンインスタンスをエクスポート
export const userActionLogger = new UserActionLogger();

// ページロード時に以前のアクションを復元
if (typeof window !== 'undefined') {
  userActionLogger.loadFromSessionStorage();
}
