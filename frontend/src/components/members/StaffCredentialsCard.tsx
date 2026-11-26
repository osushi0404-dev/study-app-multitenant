/**
 * 運営の利用者の編集画面の「パスキーと登録用リンク」の欄（I620）
 * 運営のアカウント・本人ひとりの組織の利用者には画面から出さない（裏側も 400）
 */
import { Card, CardContent, Typography } from '@mui/material';
import { useAuth } from '../../contexts/AuthContext';
import { usePasskeys } from '../../hooks/usePasskeys';
import { usePasskeyReauth } from '../../hooks/usePasskeyReauth';
import { ADMIN_USERS_BASE } from '../../services/member.service';
import PasskeyReauthDialog from '../settings/PasskeyReauthDialog';
import MemberCredentialActions from './MemberCredentialActions';

export const STAFF_NOT_AVAILABLE = 'この利用者には画面から発行できません';

type Props = {
  target: { id: string; user_id: string; is_admin: boolean; is_superuser: boolean; organization_is_individual?: boolean };
};

function StaffCredentialsCard({ target }: Props) {
  const { user } = useAuth();
  const viewerId = user?.id ?? '';
  const ownPasskeys = usePasskeys(viewerId);
  const reauth = usePasskeyReauth();
  const unavailable = target.is_admin || target.is_superuser || target.organization_is_individual
    || target.id === viewerId;

  return (
    <Card variant="outlined" sx={{ mt: 3 }}>
      <CardContent>
        <Typography variant="h6" component="h2" gutterBottom>
          パスキーと登録用リンク
        </Typography>
        {unavailable ? (
          <Typography color="text.secondary">{STAFF_NOT_AVAILABLE}</Typography>
        ) : (
          <MemberCredentialActions
            base={ADMIN_USERS_BASE}
            viewerId={viewerId}
            memberId={target.id}
            userId={target.user_id}
            hasOpenLink
            withReauth={reauth.withReauth}
          />
        )}
      </CardContent>
      <PasskeyReauthDialog
        open={reauth.dialogOpen}
        hasPasskeys={ownPasskeys.list.status === 'success' && ownPasskeys.list.data.length > 0}
        onSuccess={reauth.complete}
        onCancel={reauth.cancel}
      />
    </Card>
  );
}

export default StaffCredentialsCard;
