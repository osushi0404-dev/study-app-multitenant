import { useCallback } from 'react';
import { userActionLogger } from '../utils/userActionLogger';

/**
 * コンポーネントで操作ログを簡単に記録するためのフック
 */
export const useActionLogger = (componentName: string) => {
  const logClick = useCallback(
    (elementId?: string, details?: any) => {
      userActionLogger.logClick(componentName, elementId, details);
    },
    [componentName]
  );

  const logInput = useCallback(
    (fieldName: string, value: any, previousValue?: any) => {
      userActionLogger.logInput(componentName, fieldName, value, previousValue);
    },
    [componentName]
  );

  const logSubmit = useCallback(
    (formData: any) => {
      userActionLogger.logSubmit(componentName, formData);
    },
    [componentName]
  );

  const logError = useCallback(
    (error: any) => {
      userActionLogger.logError(componentName, error);
    },
    [componentName]
  );

  const logAction = useCallback(
    (actionType: string, details: any) => {
      userActionLogger.log({
        actionType: actionType as any,
        component: componentName,
        details,
      });
    },
    [componentName]
  );

  return {
    logClick,
    logInput,
    logSubmit,
    logError,
    logAction,
  };
};

export default useActionLogger;