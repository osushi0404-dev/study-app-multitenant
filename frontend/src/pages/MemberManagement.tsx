/**
 * メンバー管理（組織の管理者・I620）
 * - 自分の組織の利用者の一覧・ユーザー ID だけでの追加・登録用リンクの発行と取り消し・パスキーの一覧と削除
 * - 本人ひとりの組織の管理者には出さない（メニューも出さず、API も 403）
 * - 本人確認（usePasskeyReauth）は画面に 1 つだけ置き、行どうしで印を共有する
 */
import { useState } from 'react';
import toast from 'react-hot-toast';
import {
  Alert,
  Box,
  Button,
  Pagination,
  Paper,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { PersonAdd } from '@mui/icons-material';

import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../contexts/AuthContext';
import { membersKeyRoot, useMembers } from '../hooks/useMembers';
import { usePasskeys } from '../hooks/usePasskeys';
import { ReauthCancelledError, usePasskeyReauth } from '../hooks/usePasskeyReauth';
import { credentialApi, MEMBERS_BASE } from '../services/member.service';
import { Member, RegistrationLinkIssued } from '../types/api';
import { apiErrorText } from '../utils/passkeyErrors';
import AddMemberDialog from '../components/members/AddMemberDialog';
import MemberCredentialActions, { ISSUE_FAILED } from '../components/members/MemberCredentialActions';
import RegistrationLinkDialog from '../components/members/RegistrationLinkDialog';
import PasskeyReauthDialog from '../components/settings/PasskeyReauthDialog';

const PAGE_SIZE = 20;  // 裏側の REST_FRAMEWORK['PAGE_SIZE'] と同じ（ページ数を count から出すため）

const formatTime = (value: string) =>
  new Intl.DateTimeFormat('ja-JP', { timeZone: 'Asia/Tokyo', hour: '2-digit', minute: '2-digit' })
    .format(new Date(value));

export const NO_ACCESS = 'このページにアクセスする権限がありません';

const linkLabel = (member: Member): string => {
  if (member.is_self) return '—';
  const expiresAt = member.registration_link_expires_at;
  return expiresAt ? `有効（${formatTime(expiresAt)} まで）` : 'なし';
};

function MemberManagement() {
  const { user } = useAuth();
  // 本人ひとりの組織の管理者には中身を描かない（一覧の API も呼ばない）
  if (user?.organization_is_individual) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{NO_ACCESS}</Alert>
      </Box>
    );
  }
  return <MemberManagementContent viewerId={user?.id ?? ''} />;
}

function MemberManagementContent({ viewerId }: { viewerId: string }) {
  const [page, setPage] = useState(1);
  const [adding, setAdding] = useState(false);
  const [added, setAdded] = useState<{ userId: string; link: RegistrationLinkIssued } | null>(null);
  const queryClient = useQueryClient();
  const { list, create } = useMembers(viewerId, page);
  const ownPasskeys = usePasskeys(viewerId);
  const reauth = usePasskeyReauth();

  // 追加 → 本人確認 → 発行を、この画面で続けて行う（追加した人が今のページに無くても発行する・I620 F1）
  const handleAdd = async (userId: string) => {
    const member = await create.mutateAsync(userId);
    setAdding(false);
    toast.success('メンバーを追加しました');
    try {
      const link = await reauth.withReauth((token) => credentialApi(MEMBERS_BASE).issueLink(token, member.id));
      setAdded({ userId: member.user_id ?? userId, link });
      toast.success('登録用リンクを発行しました');
      queryClient.invalidateQueries({ queryKey: membersKeyRoot(viewerId) });
    } catch (error) {
      if (!(error instanceof ReauthCancelledError)) toast.error(apiErrorText(error, ISSUE_FAILED));
    }
  };

  const renderRow = (member: Member) => (
    <TableRow key={member.id}>
      <TableCell sx={{ overflowWrap: 'anywhere' }}>{member.user_id}</TableCell>
      <TableCell>{member.role === 'admin' ? '管理者' : 'メンバー'}{member.is_active ? '' : '（無効）'}</TableCell>
      <TableCell>{member.passkey_count} 個</TableCell>
      <TableCell>{linkLabel(member)}</TableCell>
      <TableCell>
        {member.is_self ? (
          <Typography variant="body2" color="text.secondary">（自分は操作できません）</Typography>
        ) : (
          <MemberCredentialActions
            base={MEMBERS_BASE}
            viewerId={viewerId}
            memberId={member.id}
            userId={member.user_id ?? ""}
            hasOpenLink={member.registration_link_expires_at !== null}
            withReauth={reauth.withReauth}
          />
        )}
      </TableCell>
    </TableRow>
  );

  const renderBody = () => {
    if (list.status === 'loading') {
      return <Skeleton variant="rounded" height={160} aria-label="メンバーを読み込み中" />;
    }
    if (list.status === 'error') {
      return (
        <Alert severity="error" action={<Button color="inherit" onClick={list.retry}>再読み込み</Button>}>
          メンバーを読み込めませんでした
        </Alert>
      );
    }
    if (list.data.results.length === 0) {
      return <Typography color="text.secondary">メンバーはまだいません</Typography>;
    }
    const pages = Math.ceil(list.data.count / PAGE_SIZE);
    return (
      <>
        <TableContainer component={Paper} sx={{ overflowX: 'auto' }}>
          <Table size="small" aria-label="メンバーの一覧">
            <TableHead>
              <TableRow>
                <TableCell component="th">ユーザーID</TableCell>
                <TableCell component="th">役割</TableCell>
                <TableCell component="th">パスキー</TableCell>
                <TableCell component="th">登録用リンク</TableCell>
                <TableCell component="th">操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>{list.data.results.map(renderRow)}</TableBody>
          </Table>
        </TableContainer>
        {pages > 1 && (
          <Pagination count={pages} page={page} onChange={(_, value) => setPage(value)} sx={{ mt: 2 }} />
        )}
      </>
    );
  };

  return (
    <Box sx={{ p: { xs: 1, sm: 3 } }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, gap: 1, flexWrap: 'wrap' }}>
        <Typography variant="h4" component="h1">メンバー管理</Typography>
        <Button variant="contained" startIcon={<PersonAdd />} onClick={() => setAdding(true)} sx={{ minHeight: 44 }}>
          メンバーを追加
        </Button>
      </Box>
      {renderBody()}
      <AddMemberDialog open={adding} onAdd={handleAdd} onCancel={() => setAdding(false)} />
      <RegistrationLinkDialog userId={added?.userId ?? ''} link={added?.link ?? null} onClose={() => setAdded(null)} />
      <PasskeyReauthDialog
        open={reauth.dialogOpen}
        hasPasskeys={ownPasskeys.list.status === 'success' && ownPasskeys.list.data.length > 0}
        onSuccess={reauth.complete}
        onCancel={reauth.cancel}
      />
    </Box>
  );
}

export default MemberManagement;
