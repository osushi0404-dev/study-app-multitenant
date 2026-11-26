/**
 * 1 人分のパスキーの一覧・削除と、登録用リンクの発行・失効（I620）
 * メンバー管理（/api/members/）と運営の編集画面（/api/admin/users/）で同じフックを使う
 */
import { useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { credentialApi, CredentialBase } from '../services/member.service';
import { toLoadState } from './queryLoadState';
import { membersKeyRoot } from './useMembers';

export const memberPasskeysKey = (viewerId: string, base: CredentialBase, memberId: string) =>
  ['member-passkeys', viewerId, base, memberId] as const;

export const useMemberCredentials = (
  viewerId: string,
  base: CredentialBase,
  memberId: string,
  { passkeysEnabled }: { passkeysEnabled: boolean }
) => {
  const queryClient = useQueryClient();
  const api = useMemo(() => credentialApi(base), [base]);
  const key = memberPasskeysKey(viewerId, base, memberId);

  const passkeysQuery = useQuery({
    queryKey: key,
    queryFn: async () => (await api.passkeys(memberId)).results,
    enabled: passkeysEnabled,
  });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: key });
    queryClient.invalidateQueries({ queryKey: membersKeyRoot(viewerId) });
  };

  const deletePasskey = useMutation({
    mutationFn: ({ reauthToken, passkeyId }: { reauthToken: string; passkeyId: string }) =>
      api.deletePasskey(reauthToken, memberId, passkeyId),
    onSuccess: refresh,
  });

  const issueLink = useMutation({
    mutationFn: (reauthToken: string) => api.issueLink(reauthToken, memberId),
    onSuccess: refresh,
  });

  const revokeLink = useMutation({
    mutationFn: (reauthToken: string) => api.revokeLink(reauthToken, memberId),
    onSuccess: refresh,
  });

  return { passkeys: toLoadState(passkeysQuery), deletePasskey, issueLink, revokeLink };
};
