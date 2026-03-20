import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import notificationService, { NotificationPermission } from '../services/notification.service';
import dashboardService from '../services/dashboard.service';
import { UserSettings } from '../services/types';
import { toast } from 'react-hot-toast';

interface NotificationContextType {
  permission: NotificationPermission;
  isEnabled: boolean;
  requestPermission: () => Promise<NotificationPermission>;
  scheduleReminders: (settings: UserSettings) => void;
  cancelReminders: () => void;
  testNotification: () => void;
  showAchievement: (message: string) => void;
  showStreakNotification: (days: number) => void;
  activeRemindersCount: number;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

interface NotificationProviderProps {
  children: ReactNode;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const [permission, setPermission] = useState<NotificationPermission>('default');
  const [currentReminderId, setCurrentReminderId] = useState<string | null>(null);
  const [activeRemindersCount, setActiveRemindersCount] = useState(0);

  useEffect(() => {
    // Initialize notification permission status
    const currentPermission = notificationService.getPermissionStatus();
    setPermission(currentPermission);
    
    // Load user settings and schedule reminders if enabled
    loadUserSettingsAndScheduleReminders();

    // Update active reminders count
    updateActiveRemindersCount();

    // Set up periodic update of reminders count
    const interval = setInterval(updateActiveRemindersCount, 60000); // Update every minute

    return () => {
      clearInterval(interval);
    };
  }, []);

  const loadUserSettingsAndScheduleReminders = async () => {
    try {
      const settings = await dashboardService.getUserSettings();
      if (settings.study_reminder_enabled && permission === 'granted') {
        scheduleReminders(settings);
      }
    } catch (error) {
      console.error('Error loading user settings for notifications:', error);
    }
  };

  const updateActiveRemindersCount = () => {
    const count = notificationService.getActiveRemindersCount();
    setActiveRemindersCount(count);
  };

  const requestPermission = async (): Promise<NotificationPermission> => {
    try {
      const newPermission = await notificationService.requestPermission();
      setPermission(newPermission);
      
      if (newPermission === 'granted') {
        // Reload settings and schedule reminders
        loadUserSettingsAndScheduleReminders();
      }
      
      return newPermission;
    } catch (error) {
      console.error('Error requesting notification permission:', error);
      return 'denied';
    }
  };

  const scheduleReminders = (settings: UserSettings) => {
    if (!notificationService.isEnabled()) {
      console.warn('Cannot schedule reminders: notifications not enabled');
      return;
    }

    // Cancel existing reminders
    cancelReminders();

    if (settings.study_reminder_enabled && settings.study_reminder_time) {
      const reminderId = notificationService.scheduleStudyReminder(
        settings.study_reminder_time,
        `今日の学習目標は${settings.daily_study_goal}分です。一緒に頑張りましょう！`
      );
      setCurrentReminderId(reminderId);
      updateActiveRemindersCount();
      
      console.log(`Study reminder scheduled for ${settings.study_reminder_time}`);
    }
  };

  const cancelReminders = () => {
    if (currentReminderId) {
      notificationService.cancelStudyReminder(currentReminderId);
      setCurrentReminderId(null);
    }
    
    // Cancel all reminders to be safe
    notificationService.cancelAllReminders();
    updateActiveRemindersCount();
  };

  const testNotification = () => {
    if (!notificationService.isEnabled()) {
      toast.error('通知が有効になっていません。設定で通知を有効にしてください。');
      return;
    }
    
    notificationService.testNotification();
  };

  const showAchievement = (message: string) => {
    if (notificationService.isEnabled()) {
      notificationService.showAchievementNotification(message);
    }
  };

  const showStreakNotification = (days: number) => {
    if (notificationService.isEnabled()) {
      notificationService.showStreakNotification(days);
    }
  };

  const value: NotificationContextType = {
    permission,
    isEnabled: notificationService.isEnabled(),
    requestPermission,
    scheduleReminders,
    cancelReminders,
    testNotification,
    showAchievement,
    showStreakNotification,
    activeRemindersCount,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

export default NotificationContext;