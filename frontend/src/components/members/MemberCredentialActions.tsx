/**
 * 1 人分の［登録用リンク］［パスキー］［リンクを取り消す］と、その確認・表示のダイアログ（I620）
 * メンバー管理と運営の編集画面で使う。本人確認（withReauth）は画面に 1 つだけ置き、行どうしで印を共有する
 */
import { useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { Box, Button } from '@mui/material';
import { Key, Link as LinkIcon, LinkOff } from '@mui/icons-material';
import { useMemberCredentials } from '../../hooks/useMemberCredentials';
import { ReauthCancelledError } from '../../hooks/usePasskeyReauth';
import { CredentialBase } from '../../services/member.service';
import { Passkey, RegistrationLinkIssued } from '../../types/api';
import { apiErrorText } from '../../utils/passkeyErrors';
import IssueLinkConfirmDialog, { LinkConfirmKind } from './IssueLinkConfirmDialog';
import MemberPasskeysDialog from './MemberPasskeysDialog';
import RegistrationLinkDialog from './RegistrationLinkDialog';

export type WithReauth = <T>(action: (token: string) => Promise<T>) => Promise<T>;

const ISSUE_FAILED = '登録用リンクを発行できませんでした。もう一度お試しください';
const REVOKE_FAILED = '登録用リンクを取り消せませんでした。もう一度お試しください';
const DELETE_FAILED = 'パスキーを削除できませんでした。もう一度お試しください';

type Props = {
  base: CredentialBase;
  viewerId: string;
  memberId: string;
  userId: string;
  hasOpenLink: boolean;
  withReauth: WithReauth;
  /** 作ったばかりの人に、確認なしで続けて発行する（メンバーを追加の流れ） */
  autoIssue?: boolean;
  onAutoIssueDone?: () => void;
};

function MemberCredentialActions({
  base, viewerId, memberId, userId, hasOpenLink, withReauth, autoIssue = false, onAutoIssueDone,
}: Props) {
  const [confirm, setConfirm] = useState<LinkConfirmKind | null>(null);
  const [issued, setIssued] = useState<RegistrationLinkIssued | null>(null);
  const [passkeysOpen, setPasskeysOpen] = useState(false);
  const [passkeyError, setPasskeyError] = useState<string | null>(null);
  const credentials = useMemberCredentials(viewerId, base, memberId, { passkeysEnabled: passkeysOpen });
  const autoIssued = useRef(false);

  const run = async <T,>(action: (token: string) => Promise<T>, failed: string): Promise<T | null> => {
    try {
      return await withReauth(action);
    } catch (error) {
      if (!(error instanceof ReauthCancelledError)) toast.error(apiErrorText(error, failed));
      return null;
    }
  };

  const issue = async () => {
    const link = await run((token) => credentials.issueLink.mutateAsync(token), ISSUE_FAILED);
    if (link) {
      setIssued(link);
      toast.success('登録用リンクを発行しました');
    }
  };

  useEffect(() => {
    if (!autoIssue || autoIssued.current) return;
    autoIssued.current = true;
    issue().finally(() => onAutoIssueDone?.());
    // 作った直後に 1 回だけ流す
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoIssue]);

  const handleConfirm = async () => {
    const kind = confirm;
    setConfirm(null);
    if (kind === 'issue') {
      await issue();
    } else if (kind === 'revoke') {
      const done = await run(async (token) => {
        await credentials.revokeLink.mutateAsync(token);
        return true;
      }, REVOKE_FAILED);
      if (done) toast.success('登録用リンクを取り消しました');
    }
  };

  const handleDeletePasskey = async (passkey: Passkey) => {
    setPasskeyError(null);
    try {
      await withReauth((token) => credentials.deletePasskey.mutateAsync({ reauthToken: token, passkeyId: passkey.id }));
      toast.success('パスキーを削除しました');
    } catch (error) {
      if (!(error instanceof ReauthCancelledError)) setPasskeyError(apiErrorText(error, DELETE_FAILED));
    }
  };

  return (
    <>
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        <Button
          size="small"
          variant="outlined"
          startIcon={<LinkIcon />}
          onClick={() => setConfirm('issue')}
          disabled={credentials.issueLink.isPending}
          sx={{ minHeight: 44 }}
        >
          登録用リンク
        </Button>
        <Button
          size="small"
          variant="outlined"
          startIcon={<Key />}
          onClick={() => { setPasskeyError(null); setPasskeysOpen(true); }}
          sx={{ minHeight: 44 }}
        >
          パスキー
        </Button>
        {hasOpenLink && (
          <Button
            size="small"
            color="error"
            startIcon={<LinkOff />}
            onClick={() => setConfirm('revoke')}
            sx={{ minHeight: 44 }}
          >
            リンクを取り消す
          </Button>
        )}
      </Box>
      <IssueLinkConfirmDialog
        userId={userId}
        kind={confirm}
        onConfirm={handleConfirm}
        onCancel={() => setConfirm(null)}
      />
      <RegistrationLinkDialog userId={userId} link={issued} onClose={() => setIssued(null)} />
      <MemberPasskeysDialog
        open={passkeysOpen}
        userId={userId}
        passkeys={credentials.passkeys}
        error={passkeyError}
        onDelete={handleDeletePasskey}
        onClose={() => setPasskeysOpen(false)}
      />
    </>
  );
}

export default MemberCredentialActions;
