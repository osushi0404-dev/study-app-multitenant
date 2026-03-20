import { toast } from 'react-hot-toast';

export type NotificationPermission = 'default' | 'granted' | 'denied';

interface StudyReminderOptions {
  title: string;
  body: string;
  icon?: string;
  badge?: string;
  tag?: string;
  renotify?: boolean;
}

class NotificationService {
  private permission: NotificationPermission = 'default';
  private reminderTimeouts: Map<string, NodeJS.Timeout> = new Map();

  constructor() {
    this.permission = this.getPermissionStatus();
  }

  // Get current notification permission status
  getPermissionStatus(): NotificationPermission {
    if (!('Notification' in window)) {
      return 'denied';
    }
    return Notification.permission as NotificationPermission;
  }

  // Request permission for notifications
  async requestPermission(): Promise<NotificationPermission> {
    if (!('Notification' in window)) {
      toast.error('このブラウザは通知をサポートしていません');
      return 'denied';
    }

    if (this.permission === 'granted') {
      return 'granted';
    }

    try {
      const permission = await Notification.requestPermission();
      this.permission = permission as NotificationPermission;
      
      if (permission === 'granted') {
        toast.success('通知が有効になりました');
      } else {
        toast.error('通知の権限が拒否されました');
      }
      
      return this.permission;
    } catch (error) {
      console.error('Error requesting notification permission:', error);
      toast.error('通知の権限取得に失敗しました');
      return 'denied';
    }
  }

  // Show a notification
  showNotification(options: StudyReminderOptions): Notification | null {
    if (!this.isSupported()) {
      console.warn('Notifications not supported');
      return null;
    }

    if (this.permission !== 'granted') {
      console.warn('Notification permission not granted');
      return null;
    }

    try {
      const notification = new Notification(options.title, {
        body: options.body,
        icon: options.icon || '/favicon.ico',
        badge: options.badge || '/favicon.ico',
        tag: options.tag || 'study-reminder',
        renotify: options.renotify || false,
        requireInteraction: true, // Keep notification until user interacts
        silent: false,
      });

      // Auto-close after 10 seconds if not interacted with
      setTimeout(() => {
        notification.close();
      }, 10000);

      // Handle notification click
      notification.onclick = () => {
        window.focus();
        notification.close();
        // Navigate to the app if not already focused
        if (document.hidden) {
          window.location.href = '/dashboard';
        }
      };

      return notification;
    } catch (error) {
      console.error('Error showing notification:', error);
      return null;
    }
  }

  // Schedule a study reminder
  scheduleStudyReminder(time: string, message?: string): string {
    const now = new Date();
    const [hours, minutes] = time.split(':').map(Number);
    
    // Create target time for today
    const targetTime = new Date();
    targetTime.setHours(hours, minutes, 0, 0);
    
    // If target time has passed today, schedule for tomorrow
    if (targetTime <= now) {
      targetTime.setDate(targetTime.getDate() + 1);
    }
    
    const timeUntilReminder = targetTime.getTime() - now.getTime();
    const reminderId = `reminder-${Date.now()}`;
    
    const timeout = setTimeout(() => {
      this.showStudyReminder(message);
      // Schedule next day's reminder
      this.scheduleStudyReminder(time, message);
    }, timeUntilReminder);
    
    this.reminderTimeouts.set(reminderId, timeout);
    
    console.log(`Study reminder scheduled for ${targetTime.toLocaleString()}`);
    return reminderId;
  }

  // Cancel a scheduled reminder
  cancelStudyReminder(reminderId: string): boolean {
    const timeout = this.reminderTimeouts.get(reminderId);
    if (timeout) {
      clearTimeout(timeout);
      this.reminderTimeouts.delete(reminderId);
      return true;
    }
    return false;
  }

  // Cancel all scheduled reminders
  cancelAllReminders(): void {
    this.reminderTimeouts.forEach((timeout) => {
      clearTimeout(timeout);
    });
    this.reminderTimeouts.clear();
  }

  // Show study reminder notification
  showStudyReminder(customMessage?: string): Notification | null {
    const messages = [
      '学習の時間です！今日も頑張りましょう 📚',
      '勉強を始めませんか？継続は力なりです 💪',
      '学習習慣を維持しましょう！小さな積み重ねが大切です ✨',
      'クイズに挑戦して知識を深めましょう 🧠',
      '今日の目標に向かって一歩前進しましょう 🎯',
    ];

    const randomMessage = messages[Math.floor(Math.random() * messages.length)];
    const message = customMessage || randomMessage;

    return this.showNotification({
      title: '📚 学習リマインダー',
      body: message,
      tag: 'study-reminder',
      renotify: true,
    });
  }

  // Show break reminder
  showBreakReminder(): Notification | null {
    return this.showNotification({
      title: '🧘 休憩リマインダー',
      body: '適度な休憩を取って、リフレッシュしましょう！',
      tag: 'break-reminder',
    });
  }

  // Show achievement notification
  showAchievementNotification(achievement: string): Notification | null {
    return this.showNotification({
      title: '🎉 達成おめでとうございます！',
      body: achievement,
      tag: 'achievement',
    });
  }

  // Show streak notification
  showStreakNotification(streakDays: number): Notification | null {
    return this.showNotification({
      title: '🔥 連続学習記録更新！',
      body: `${streakDays}日連続で学習しています。素晴らしいです！`,
      tag: 'streak',
    });
  }

  // Check if notifications are supported
  isSupported(): boolean {
    return 'Notification' in window;
  }

  // Check if user has granted permission
  isEnabled(): boolean {
    return this.isSupported() && this.permission === 'granted';
  }

  // Schedule study session reminders during study
  scheduleStudySessionReminders(sessionDuration: number): string[] {
    const reminderIds: string[] = [];
    
    // Remind to take a break every 25 minutes (Pomodoro technique)
    const breakInterval = 25 * 60 * 1000; // 25 minutes in milliseconds
    const numberOfBreaks = Math.floor(sessionDuration / breakInterval);
    
    for (let i = 1; i <= numberOfBreaks; i++) {
      const timeout = setTimeout(() => {
        this.showBreakReminder();
      }, i * breakInterval);
      
      const reminderId = `break-${Date.now()}-${i}`;
      this.reminderTimeouts.set(reminderId, timeout);
      reminderIds.push(reminderId);
    }
    
    return reminderIds;
  }

  // Get reminder statistics
  getActiveRemindersCount(): number {
    return this.reminderTimeouts.size;
  }

  // Test notification (for settings page)
  testNotification(): Notification | null {
    return this.showNotification({
      title: '🔔 テスト通知',
      body: '通知が正常に動作しています！',
      tag: 'test',
    });
  }
}

// Create and export singleton instance
export const notificationService = new NotificationService();
export default notificationService;